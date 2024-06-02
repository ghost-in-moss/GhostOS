from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Dict, TypeVar, Callable, Set

INSTRUCTION = """
打算实现一个 IoC 容器用来管理大量可替换的中间库. 
"""

Contract = TypeVar('Contract', bound=object)


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
        self.__instances: Dict[Type[Contract], Contract] = {}
        # providers bounds
        self.__providers: Dict[Type[Contract], Provider] = {}
        self.__bound: Set = set()

    def set(self, contract: Type[Contract], instance: Contract) -> None:
        """
        设置一个实例, 不会污染父容器.
        """
        self._bind_contract(contract)
        self.__instances[contract] = instance

    def _bind_contract(self, contract: Type[Contract]) -> None:
        self.__bound.add(contract)

    def bound(self, contract: Type[Contract]) -> bool:
        """
        return whether contract is bound.
        """
        return contract in self.__bound or (self.parent is not None and self.parent.bound(contract))

    def get(self, contract: Type[Contract], params: Dict | None = None) -> Contract | None:
        """
        get bound instance or initialize one of the contract

        # dev logs:

        - params 感觉不需要.
        """

        # get bound instance
        got = self.__instances.get(contract, None)
        if got is not None:
            return got

        # use provider as factory to initialize instance of the contract
        if contract in self.__providers:
            provider = self.__providers[contract]
            made = provider.factory(self, params)
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
        contract = provider.contract()
        self._bind_contract(contract)
        if contract in self.__instances:
            del self.__instances[contract]
        self.__providers[contract] = provider

    def fetch(self, contract: Type[Contract], strict: bool = False) -> Contract | None:
        """
        get contract with type check
        """
        instance = self.get(contract)
        if instance is not None:
            if strict and not isinstance(instance, contract):
                return None
            return instance
        return None

    def force_fetch(self, contract: Type[Contract], strict: bool = False) -> Contract:
        """
        if fetch contract failed, raise error.
        """
        ins = self.fetch(contract, strict)
        if ins is None:
            raise NotImplemented(f"contract {contract} not register in container")
        return ins

    def destroy(self) -> None:
        """
        Manually delete the container to prevent memory leaks.
        """
        del self.__instances
        del self.parent
        del self.__providers
        del self.__bound


class Provider(metaclass=ABCMeta):

    @abstractmethod
    def singleton(self) -> bool:
        """
        if singleton, return True.
        """
        pass

    @abstractmethod
    def contract(self) -> Type[Contract]:
        """
        contract for this provider.
        """
        pass

    @abstractmethod
    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        """
        factory method to generate an instance of the contract.
        """
        pass


class ProviderAdapter(Provider):
    """
    create a provider without class.
    """

    def __init__(
            self,
            contract_type: Type[Contract],
            factory: Callable[[Container, Dict | None], Contract | None],
            singleton: bool = True
    ):
        self._contract_type = contract_type
        self._factory = factory
        self._singleton = singleton

    def singleton(self) -> bool:
        return self._singleton

    def contract(self) -> Type[Contract]:
        return self._contract_type

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        return self._factory(con, params)
