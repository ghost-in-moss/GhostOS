from __future__ import annotations
import inspect
from abc import ABCMeta, abstractmethod
from typing import Type, Dict, TypeVar, Callable, Set, Optional, List, Generic, Any, Union, Iterable
from typing import get_args, get_origin, ClassVar
import warnings

__all__ = [
    "Container", "IoCContainer",
    "Provider", "Factory", "Bootstrapper", "BootstrapProvider",
    "INSTANCE", "ABSTRACT",
    "ProviderAdapter", 'provide',
    'Contracts',
    'get_caller_info',
    'get_container',
    'set_container',
]

INSTRUCTION = """
打算实现一个 IoC 容器用来管理大量可替换的中间库. 
"""

INSTANCE = TypeVar('INSTANCE')
"""instance in the container"""

ABSTRACT = Type[INSTANCE]
"""abstract of the instance"""


class IoCContainer(metaclass=ABCMeta):
    """
    Basic Design of the Inverse of Control Container.
    """

    @abstractmethod
    def set(self, abstract: ABSTRACT, instance: INSTANCE) -> None:
        """
        设置一个实例, 不会污染父容器.
        """

    @abstractmethod
    def register(self, *providers: Provider) -> None:
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
    def get(self, abstract: Type[INSTANCE]) -> Optional[INSTANCE]:
        """
        get bound instance or initialize one from registered abstract, or generate one by factory or provider.
        :return: None if no bound instance.
        """
        pass

    @abstractmethod
    def get_bound(self, abstract: Type[INSTANCE]) -> Union[INSTANCE, Provider, None]:
        """
        get bound of an abstract
        useful to debug
        :return: instance or provider
        """
        pass

    @abstractmethod
    def get_provider(self, abstract: Type[INSTANCE]) -> Optional[Provider[INSTANCE]]:
        pass

    @abstractmethod
    def rebind(self, abstract: Type[INSTANCE]) -> None:
        pass

    @abstractmethod
    def fetch(self, abstract: Type[INSTANCE], strict: bool = False) -> Optional[INSTANCE]:
        """
        :param abstract: use type of the object (usually an abstract class) to fetch the implementation.
        :param strict: autotype check
        :exception: TypeError if instance do not implement abstract
        """
        pass

    @abstractmethod
    def force_fetch(self, contract: Type[INSTANCE], strict: bool = False) -> INSTANCE:
        """
        if fetch contract failed, raise error.
        :exception: NotImplementedError if contract is not registered.
        :exception: TypeError if contract do not implement abstract
        """
        pass

    @abstractmethod
    def bound(self, contract: Type[INSTANCE]) -> bool:
        """
        return whether contract is bound.
        """
        pass

    @abstractmethod
    def contracts(self, recursively: bool = True) -> Iterable[ABSTRACT]:
        """
        yield from bound contracts
        """
        pass

    @abstractmethod
    def providers(self, recursively: bool = True) -> Iterable[Provider]:
        pass

    @abstractmethod
    def shutdown(self) -> None:
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
    instance_count: ClassVar[int] = 0
    bloodline: List[str]

    def __init__(self, parent: Optional[Container] = None, *, name: str = "", inherit: bool = True):
        self.bloodline = []
        # container extended by children container
        if parent is not None:
            if not isinstance(parent, Container):
                raise AttributeError("container can only initialized with parent Container")
            if parent is self:
                raise AttributeError("container's parent must not be itself")
        self.parent: Optional[Container] = parent
        if isinstance(self.parent, Container):
            bloodline = self.parent.bloodline.copy()
            bloodline.append(name)
        else:
            bloodline = [name]
        self.bloodline: List[str] = bloodline

        # global singletons.
        self._instances: Dict[Any, Any] = {}
        self._factory: Dict[Any, Factory] = {}
        # providers bounds
        self._providers: Dict[Any, Provider] = {}
        self._bound: Set = set()
        self._bootstrapper: List["Bootstrapper"] = []
        self._bootstrapped: bool = False
        self._aliases: Dict[Any, Any] = {}
        self._is_shutdown: bool = False
        self._shutdown: List[Callable[[], None]] = []
        if inherit and parent is not None:
            self._inherit(parent)

        Container.instance_count += 1

    def _inherit(self, parent: Container):
        """
        inherit none singleton provider from parent
        """
        for provider in parent.providers(recursively=True):
            if provider.inheritable() and not isinstance(provider, Bootstrapper):
                self._register(provider)

    def bootstrap(self) -> None:
        """
        执行 bootstrap, 只执行一次. 可以操作依赖关系. 比如实例化后反向注册.
        """
        self._check_destroyed()
        if self._bootstrapped:
            return
        # 必须在这里初始化, 否则会循环调用.
        self._bootstrapped = True
        if self._bootstrapper:
            for b in self._bootstrapper:
                b.bootstrap(self)
        for provider in self._providers.values():
            # some bootstrapper provider may be override
            if isinstance(provider, Bootstrapper):
                provider.bootstrap(self)

    def add_shutdown(self, shutdown: Callable):
        self._shutdown.append(shutdown)

    def set(self, abstract: Any, instance: INSTANCE) -> None:
        """
        设置一个实例, 不会污染父容器.
        """
        self._check_destroyed()
        if abstract in self._providers:
            del self._providers[abstract]
        self._set_instance(abstract, instance)

    def _add_bound_contract(self, abstract: ABSTRACT) -> None:
        """
        添加好绑定关系, 方便快速查找.
        """
        self._bound.add(abstract)

    def bound(self, contract: Type) -> bool:
        """
        return whether contract is bound.
        """
        self._check_destroyed()
        return contract in self._bound or (self.parent is not None and self.parent.bound(contract))

    def get(self, abstract: Union[Type[INSTANCE], Any]) -> Optional[INSTANCE]:
        """
        get bound instance or initialize one from registered factory or provider.

        # dev logs:

        - params 感觉不需要.
        """
        self._check_destroyed()
        # 进行初始化.
        if not self._bootstrapped:
            warnings.warn("container is not bootstrapped before using")
            self.bootstrap()

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

        # search aliases if the real contract exists
        if abstract in self._aliases:
            contract = self._aliases[abstract]
            return self.get(contract)

        # at last
        if self.parent is not None:
            return self.parent.get(abstract)
        return None

    def get_bound(self, abstract: ABSTRACT) -> Union[INSTANCE, Provider, None]:
        """
        get bound of an abstract
        :return: instance or provider
        """
        self._check_destroyed()
        if abstract in self._instances:
            return self._instances[abstract]
        elif abstract in self._providers:
            return self._providers[abstract]
        elif abstract in self._aliases:
            alias = self._aliases[abstract]
            return alias
        elif self.parent is not None:
            return self.parent.get_bound(abstract)
        return None

    def register_maker(
            self,
            contract: ABSTRACT,
            maker: Callable[[], INSTANCE],
            singleton: bool = False,
    ):
        self._check_destroyed()
        lineinfo = get_caller_info(2)

        def _maker(c):
            return maker()

        provider = provide(contract, singleton=singleton, lineinfo=lineinfo)(_maker)
        self.register(provider)

    def register(self, *providers: Provider) -> None:
        """
        register factory of the contract by provider
        """
        self._check_destroyed()
        for provider in providers:
            self._register(provider)

    def _register(self, provider: Provider) -> None:
        contract = provider.contract()
        self._add_bound_contract(contract)
        self._register_provider(contract, provider)

        # additional bindings
        for alias in provider.aliases():
            if alias not in self._bound:
                self._bind_alias(alias, contract)
        if isinstance(provider, Bootstrapper) and self._bootstrapped:
            # 添加 bootstrapper.
            provider.bootstrap(self)

    def _bind_alias(self, alias: Any, contract: Any) -> None:
        self._aliases[alias] = contract
        self._bound.add(alias)

    def _register_provider(self, contract: ABSTRACT, provider: Provider) -> None:
        # remove singleton instance that already bound
        if contract in self._instances:
            del self._instances[contract]
        # override the existing one
        self._providers[contract] = provider

    def add_bootstrapper(self, bootstrapper: Bootstrapper) -> None:
        """
        注册 Container 的 bootstrapper. 在正式运行时会先 bootstrap, 而且只执行一次.
        :param bootstrapper: 可以定义一些方法, 比如往容器里的某个类里注册一些工具.
        :return:
        """
        self._check_destroyed()
        if not self._bootstrapped:
            self._bootstrapper.append(bootstrapper)

    def fetch(self, abstract: Type[INSTANCE], strict: bool = False) -> Optional[INSTANCE]:
        """
        get contract with type check
        :exception: TypeError if instance do not implement abstract
        """
        self._check_destroyed()
        instance = self.get(abstract)
        if instance is not None:
            if strict and not isinstance(instance, abstract):
                raise TypeError(f"bound implements is not type of {abstract}")
            return instance
        return None

    def get_provider(self, abstract: Type[INSTANCE]) -> Optional[Provider[INSTANCE]]:
        if abstract in self._providers:
            return self._providers[abstract]
        if self.parent is not None:
            return self.parent.get_provider(abstract)
        return None

    def rebind(self, abstract: Type[INSTANCE]) -> None:
        provider = self.get_provider(abstract)
        if provider is not None:
            self.register(provider)

    def force_fetch(self, contract: Type[INSTANCE], strict: bool = False) -> INSTANCE:
        """
        if fetch contract failed, raise error.
        :exception: NotImplementedError if contract is not registered.
        :exception: TypeError if contract do not implement abstract
        """
        self._check_destroyed()
        ins = self.fetch(contract, strict)
        if ins is None:
            raise NotImplementedError(f"contract {contract} not register in container")
        return ins

    def _set_instance(self, abstract: Any, instance: Any) -> None:
        """
        设定常量.
        """
        self._add_bound_contract(abstract)
        self._instances[abstract] = instance

    def contracts(self, recursively: bool = True) -> Iterable[ABSTRACT]:
        self._check_destroyed()
        done = set()
        for contract in self._bound:
            done.add(contract)
            yield contract
        if recursively and self.parent is not None:
            for contract in self.parent.contracts():
                if contract not in done:
                    done.add(contract)
                    yield contract

    def providers(self, recursively: bool = True) -> Iterable[Provider]:
        self._check_destroyed()
        done = set()
        for provider in self._providers.values():
            done.add(provider.contract())
            yield provider
        if recursively and self.parent is not None:
            for provider in self.parent.providers():
                if provider.contract() not in done:
                    done.add(provider.contract())
                    yield provider

    def _check_destroyed(self) -> None:
        if self._is_shutdown:
            raise RuntimeError(f"container {self.bloodline} is called after destroyed")

    def shutdown(self) -> None:
        """
        Manually delete the container to prevent memory leaks.
        """
        if self._is_shutdown:
            return
        self._is_shutdown = True
        for shutdown in self._shutdown:
            shutdown()

    def __del__(self):
        self.shutdown()
        del self._shutdown
        del self._instances
        del self.parent
        del self._providers
        del self._bound
        del self._bootstrapper
        del self._bootstrapped
        del self._aliases
        Container.instance_count -= 1


Factory = Callable[[Container], Any]


class Provider(Generic[INSTANCE], metaclass=ABCMeta):

    @abstractmethod
    def singleton(self) -> bool:
        """
        if singleton, return True.
        """
        pass

    def inheritable(self) -> bool:
        """
        if the provider is inheritable to sub container
        """
        return not self.singleton()

    def contract(self) -> ABSTRACT:
        """
        :return: contract for this provider.
        override this method to define a contract without get from generic args
        """
        return get_contract_type(self.__class__)

    def aliases(self) -> Iterable[ABSTRACT]:
        """
        additional contracts that shall bind to this provider if the binding contract is not Bound.
        """
        return []

    @abstractmethod
    def factory(self, con: Container) -> Optional[INSTANCE]:
        """
        factory method to generate an instance of the contract.
        """
        pass


def get_contract_type(cls: Type[Provider]) -> ABSTRACT:
    """
    get generic INSTANCE type from the instance of the provider.
    """
    if "__orig_bases__" in cls.__dict__:
        orig_bases = getattr(cls, "__orig_bases__")
        for parent in orig_bases:
            if get_origin(parent) is not Provider:
                continue
            args = get_args(parent)
            if not args:
                break
            return args[0]
    raise AttributeError("can not get contract type")


class Bootstrapper(metaclass=ABCMeta):
    """
    完成所有的绑定之后, 进行容器之间的初始化.
    """

    @abstractmethod
    def bootstrap(self, container: Container) -> None:
        pass


class BootstrapProvider(Generic[INSTANCE], Provider[INSTANCE], Bootstrapper, metaclass=ABCMeta):
    """
    将 bootstrapper 和 Provider 可以融合在一起.
    """

    @abstractmethod
    def contract(self) -> Type[INSTANCE]:
        pass


class ProviderAdapter(Generic[INSTANCE], Provider[INSTANCE]):
    """
    create a provider without class.
    """

    def __init__(
            self,
            contract_type: Type[INSTANCE],
            factory: Callable[[Container], Optional[INSTANCE]],
            singleton: bool = True,
            lineinfo: str = "",
    ):
        self._contract_type = contract_type
        self._factory = factory
        self._singleton = singleton
        self._lineinfo = lineinfo

    def singleton(self) -> bool:
        return self._singleton

    def contract(self) -> Type[INSTANCE]:
        return self._contract_type

    def factory(self, con: Container) -> Optional[INSTANCE]:
        return self._factory(con)

    def __repr__(self):
        if self._lineinfo:
            return f" <ghostos.container.ProviderAdapter for {self.contract()} at {self._lineinfo}>"
        return f" <ghostos.container.ProviderAdapter for {self.contract()}>"


def get_caller_info(backtrace: int = 1, with_full_file: bool = True) -> str:
    stack = inspect.stack()
    # 获取调用者的上下文信息
    caller_frame_record = stack[backtrace]
    frame = caller_frame_record[0]
    info = inspect.getframeinfo(frame)
    filename = info.filename
    if not with_full_file:
        filename = filename.split("/")[-1]
    return f"{filename}:{info.lineno}"


def provide(
        abstract: ABSTRACT,
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


class Contracts:
    """
    A contracts validator that both indicate the contract types and validate if they are bound to container
    """

    def __init__(self, contracts: List[ABSTRACT]):
        self.contracts = contracts

    def validate(self, container: Container) -> None:
        for contract in self.contracts:
            if not container.bound(contract):
                call_at = get_caller_info(2)
                raise NotImplementedError(f'Contract {contract} not bound to container: {call_at}')

    def join(self, target: Contracts) -> Contracts:
        abstracts = set(self.contracts)
        for c in target.contracts:
            abstracts.add(c)
        return Contracts(list(abstracts))


__container = Container()


def get_container() -> Container:
    """
    get global static container
    """
    return __container


def set_container(container: Container) -> None:
    """
    change global static container
    may cause unexpected behavior.
    """
    global __container
    __container = container
