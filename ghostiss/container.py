from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Dict, TypeVar, Callable, Set, Optional, List, Generic

INSTRUCTION = """
打算实现一个 IoC 容器用来管理大量可替换的中间库. 
"""

CONTRACT = TypeVar('CONTRACT', bound=object)


class Container:
    """
    一个简单的 IoC 容器.
    IOC Container: 用来解耦各种 interface 和实现.

    # dev logs:
    - python 没有好用的 container (或者我没发现), 所以自己先简单封装一个.
    - 对于 MoOS 而言, Container 也是必要的. 这样可以只把 interface 暴露给 LLM, 但又可以让它使用实例.
    - 仍然需要考虑加入 RAG Memories 来支持. 获取做到 OS 层.
    """

    def __init__(self, parent: Container | None = None):
        # container extended by children container
        if parent is not None:
            if not isinstance(parent, Container):
                raise AttributeError("container can only initialized with parent Container")
            if parent is self:
                raise AttributeError("container's parent must not be itself")
        self.parent = parent
        # global singletons.
        self._instances: Dict[Type[CONTRACT], CONTRACT] = {}
        # providers bounds
        self._providers: Dict[Type[CONTRACT], Provider] = {}
        self._bound: Set = set()
        self._bootstrapper: List["Bootstrapper"] = []
        self._bootstrapped: bool = False

    def bootstrap(self) -> None:
        """
        执行 bootstrap, 只执行一次. 可以操作依赖关系. 比如实例化后反向注册.
        """
        if self._bootstrapped:
            return
        if not self._bootstrapper:
            return
        for b in self._bootstrapper:
            b.bootstrap(self)
        self._bootstrapped = True

    def set(self, contract: Type[CONTRACT], instance: CONTRACT) -> None:
        """
        设置一个实例, 不会污染父容器.
        """
        self._bind_contract(contract)
        self._instances[contract] = instance

    def _bind_contract(self, contract: Type[CONTRACT]) -> None:
        self._bound.add(contract)

    def bound(self, contract: Type[CONTRACT]) -> bool:
        """
        return whether contract is bound.
        """
        return contract in self._bound or (self.parent is not None and self.parent.bound(contract))

    def get(self, contract: Type[CONTRACT]) -> CONTRACT | None:
        """
        get bound instance or initialize one of the contract

        # dev logs:

        - params 感觉不需要.
        """
        if not self._bootstrapped:
            # 进行初始化.
            self.bootstrap()

        # get bound instance
        got = self._instances.get(contract, None)
        if got is not None:
            return got

        # use provider as factory to initialize instance of the contract
        if contract in self._providers:
            provider = self._providers[contract]
            made = provider.factory(self)
            if made is not None and provider.singleton():
                self.set(contract, made)
            return made

        # 第三优先级.
        if self.parent is not None:
            return self.parent.get(contract)
        return None

    def register(self, provider: Provider) -> None:
        """
        register factory of the contract by provider
        """
        if isinstance(provider, Bootstrapper):
            # 添加 bootstrapper.
            self.add_bootstrapper(provider)

        contract = provider.contract()
        self._bind_contract(contract)
        if contract in self._instances:
            del self._instances[contract]
        self._providers[contract] = provider

    def add_bootstrapper(self, bootstrapper: Bootstrapper) -> None:
        self._bootstrapper.append(bootstrapper)

    def fetch(self, contract: Type[CONTRACT], strict: bool = False) -> CONTRACT | None:
        """
        get contract with type check
        """
        instance = self.get(contract)
        if instance is not None:
            if strict and not isinstance(instance, contract):
                return None
            return instance
        return None

    def force_fetch(self, contract: Type[CONTRACT], strict: bool = False) -> CONTRACT:
        """
        if fetch contract failed, raise error.
        """
        ins = self.fetch(contract, strict)
        if ins is None:
            raise NotImplementedError(f"contract {contract} not register in container")
        return ins

    def destroy(self) -> None:
        """
        Manually delete the container to prevent memory leaks.
        """
        del self._instances
        del self.parent
        del self._providers
        del self._bound
        del self._bootstrapper
        del self._bootstrapped


class Provider(Generic[CONTRACT], metaclass=ABCMeta):

    @abstractmethod
    def singleton(self) -> bool:
        """
        if singleton, return True.
        """
        pass

    @abstractmethod
    def contract(self) -> Type[CONTRACT]:
        """
        contract for this provider.
        """
        pass

    @abstractmethod
    def factory(self, con: Container) -> Optional[CONTRACT]:
        """
        factory method to generate an instance of the contract.
        """
        pass


class Bootstrapper(metaclass=ABCMeta):
    """
    完成所有的绑定之后, 进行容器之间的初始化.
    """

    @abstractmethod
    def bootstrap(self, container: Container) -> None:
        pass


class BootstrappingProvider(Provider, Bootstrapper, metaclass=ABCMeta):
    """
    将 bootstrapper 和 Provider 可以融合在一起.
    """
    pass


class ProviderAdapter(Provider):
    """
    create a provider without class.
    """

    def __init__(
            self,
            contract_type: Type[CONTRACT],
            factory: Callable[[Container], Optional[CONTRACT]],
            singleton: bool = True
    ):
        self._contract_type = contract_type
        self._factory = factory
        self._singleton = singleton

    def singleton(self) -> bool:
        return self._singleton

    def contract(self) -> Type[CONTRACT]:
        return self._contract_type

    def factory(self, con: Container) -> Optional[CONTRACT]:
        return self._factory(con)
