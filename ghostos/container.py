from __future__ import annotations
import inspect
from abc import ABCMeta, abstractmethod
from typing import Type, Dict, TypeVar, Callable, Set, Optional, List, Generic, Any, Union, Iterable

__all__ = [
    "Container", "IoCContainer",
    "Provider", "Factory", "Bootstrapper",
    "ABSTRACT",
    "ProviderAdapter", 'provide',
]

INSTRUCTION = """
打算实现一个 IoC 容器用来管理大量可替换的中间库. 
"""

ABSTRACT = TypeVar('ABSTRACT', bound=object)


class IoCContainer(metaclass=ABCMeta):
    """
    Basic Design of the Inverse of Control Container.
    """

    @abstractmethod
    def set(self, abstract: Type[ABSTRACT], instance: ABSTRACT) -> None:
        """
        设置一个实例, 不会污染父容器.
        """

    @abstractmethod
    def register(self, provider: Provider) -> None:
        """
        register factory of the contract by provider
        """
        pass

    def add_bootstrapper(self, bootstrapper: Bootstrapper) -> None:
        """
        注册 Container 的 bootstrapper. 在正式运行时会先 bootstrap, 而且只执行一次.
        :param bootstrapper: 可以定义一些方法, 比如往容器里的某个类里注册一些工具.
        :return:
        """
        pass

    @abstractmethod
    def bootstrap(self) -> None:
        """
        执行 bootstrap, 将所有的 bootstrapper 执行一次.
        只执行一次. 可以操作依赖关系. 比如实例化后反向注册.
        也会在 get 的时候
        """
        pass

    @abstractmethod
    def get(self, abstract: Union[Type[ABSTRACT], Factory, Provider]) -> Optional[ABSTRACT]:
        """
        get bound instance or initialize one from registered abstract, or generate one by factory or provider.
        :return: None if no bound instance.
        """
        pass

    @abstractmethod
    def fetch(self, abstract: Type[ABSTRACT], strict: bool = False) -> Optional[ABSTRACT]:
        """
        :param abstract: use type of the object (usually an abstract class) to fetch the implementation.
        :param strict: autotype check
        :exception: TypeError if instance do not implement abstract
        """
        pass

    @abstractmethod
    def force_fetch(self, contract: Type[ABSTRACT], strict: bool = False) -> ABSTRACT:
        """
        if fetch contract failed, raise error.
        :exception: NotImplementedError if contract is not registered.
        :exception: TypeError if contract do not implement abstract
        """
        pass

    @abstractmethod
    def bound(self, contract: Type[ABSTRACT]) -> bool:
        """
        return whether contract is bound.
        """
        pass

    @abstractmethod
    def contracts(self, recursively: bool = True) -> Iterable[Type[ABSTRACT]]:
        """
        yield from bound contracts
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        Manually delete the container to prevent memory leaks.
        """
        pass


class Container(IoCContainer):
    """
    一个简单的 IoC 容器.
    IOC Container: 用来解耦各种 interface 和实现.

    # dev logs:
    - python 没有好用的 container (或者我没发现), 所以自己先简单封装一个.
    - 对于 MOSS 而言, Container 也是必要的. 这样可以只把 interface 暴露给 LLM, 但又可以让它使用实例.
    - 仍然需要考虑加入 RAG Memories 来支持. 获取做到 OS 层.
    """

    def __init__(self, parent: Optional[Container] = None):
        # container extended by children container
        if parent is not None:
            if not isinstance(parent, Container):
                raise AttributeError("container can only initialized with parent Container")
            if parent is self:
                raise AttributeError("container's parent must not be itself")
        self.parent = parent
        # global singletons.
        self._instances: Dict[Any, Any] = {}
        self._factory: Dict[Any, Factory] = {}
        # providers bounds
        self._providers: Dict[Any, Provider] = {}
        self._bound: Set = set()
        self._bootstrapper: List["Bootstrapper"] = []
        self._bootstrapped: bool = False

    def bootstrap(self) -> None:
        """
        执行 bootstrap, 只执行一次. 可以操作依赖关系. 比如实例化后反向注册.
        """
        if self._bootstrapped:
            return
        # 必须在这里初始化, 否则会循环调用.
        self._bootstrapped = True
        if not self._bootstrapper:
            return
        for b in self._bootstrapper:
            b.bootstrap(self)

    def set(self, abstract: Type[ABSTRACT], instance: ABSTRACT) -> None:
        """
        设置一个实例, 不会污染父容器.
        """
        self._set_instance(abstract, instance)

    def _bind_contract(self, abstract: Type[ABSTRACT]) -> None:
        """
        添加好绑定关系, 方便快速查找.
        """
        self._bound.add(abstract)

    def bound(self, contract: Type) -> bool:
        """
        return whether contract is bound.
        """
        return contract in self._bound or (self.parent is not None and self.parent.bound(contract))

    def get(self, abstract: Type[ABSTRACT]) -> Optional[ABSTRACT]:
        """
        get bound instance or initialize one from registered factory or provider.

        # dev logs:

        - params 感觉不需要.
        """
        # 进行初始化.
        self.bootstrap()

        if isinstance(abstract, Provider):
            return abstract.factory(self)

        # get bound instance
        got = self._instances.get(abstract, None)
        if got is not None:
            return got

        # use provider as factory to initialize instance of the contract
        if abstract in self._providers:
            provider = self._providers[abstract]
            made = provider.factory(self)
            if made is not None and provider.singleton():
                self._set_instance(abstract, made)
            return made

        # 第三优先级.
        if self.parent is not None:
            return self.parent.get(abstract)
        return None

    def register_maker(
            self,
            contract: Type[ABSTRACT],
            maker: Callable[[], ABSTRACT],
            singleton: bool = False,
    ):
        lineinfo = get_caller_info(2)

        def _maker(c):
            return maker()

        provider = provide(contract, singleton=singleton, lineinfo=lineinfo)(_maker)
        self.register(provider)

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
        """
        注册 Container 的 bootstrapper. 在正式运行时会先 bootstrap, 而且只执行一次.
        :param bootstrapper: 可以定义一些方法, 比如往容器里的某个类里注册一些工具.
        :return:
        """
        self._bootstrapper.append(bootstrapper)

    def fetch(self, abstract: Type[ABSTRACT], strict: bool = False) -> Optional[ABSTRACT]:
        """
        get contract with type check
        :exception: TypeError if instance do not implement abstract
        """
        instance = self.get(abstract)
        if instance is not None:
            if strict and not isinstance(instance, abstract):
                raise TypeError(f"bound implements is not type of {abstract}")
            return instance
        return None

    def force_fetch(self, contract: Type[ABSTRACT], strict: bool = False) -> ABSTRACT:
        """
        if fetch contract failed, raise error.
        :exception: NotImplementedError if contract is not registered.
        :exception: TypeError if contract do not implement abstract
        """
        ins = self.fetch(contract, strict)
        if ins is None:
            raise NotImplementedError(f"contract {contract} not register in container")
        return ins

    def _set_instance(self, abstract: Any, instance: Any) -> None:
        """
        设定常量.
        """
        self._bind_contract(abstract)
        self._instances[abstract] = instance

    def contracts(self, recursively: bool = True) -> Iterable[Type[ABSTRACT]]:
        done = set()
        for contract in self._bound:
            done.add(contract)
            yield contract
        if recursively and self.parent is not None:
            for contract in self.parent.contracts():
                if contract not in done:
                    done.add(contract)
                    yield contract

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


Factory = Callable[[Container], Any]


class Provider(Generic[ABSTRACT], metaclass=ABCMeta):

    @abstractmethod
    def singleton(self) -> bool:
        """
        if singleton, return True.
        """
        pass

    @abstractmethod
    def contract(self) -> Type[ABSTRACT]:
        """
        contract for this provider.
        """
        pass

    @abstractmethod
    def factory(self, con: Container) -> Optional[ABSTRACT]:
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


class BootstrappingProvider(Generic[ABSTRACT], Provider[ABSTRACT], Bootstrapper, metaclass=ABCMeta):
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
            contract_type: Type[ABSTRACT],
            factory: Callable[[Container], Optional[ABSTRACT]],
            singleton: bool = True,
            lineinfo: str = "",
    ):
        self._contract_type = contract_type
        self._factory = factory
        self._singleton = singleton
        self._lineinfo = lineinfo

    def singleton(self) -> bool:
        return self._singleton

    def contract(self) -> Type[ABSTRACT]:
        return self._contract_type

    def factory(self, con: Container) -> Optional[ABSTRACT]:
        return self._factory(con)

    def __repr__(self):
        if self._lineinfo:
            return f" <ghostos.container.ProviderAdapter for {self.contract()} at {self._lineinfo}>"
        return f" <ghostos.container.ProviderAdapter for {self.contract()}>"


def get_caller_info(backtrace: int = 1) -> str:
    stack = inspect.stack()
    # 获取调用者的上下文信息
    caller_frame_record = stack[backtrace]
    frame = caller_frame_record[0]
    info = inspect.getframeinfo(frame)
    return f"{info.filename}:{info.lineno}"


def provide(
        abstract: Type[ABSTRACT],
        singleton: bool = True,
        lineinfo: str = "",
) -> Callable[[Factory], Provider]:
    """
    helper function to generate provider with factory.
    can be used as a decorator.
    """
    if not lineinfo:
        lineinfo = get_caller_info(2)

    def wrapper(factory: Factory) -> Provider:
        return ProviderAdapter(abstract, factory, singleton, lineinfo=lineinfo)

    return wrapper
