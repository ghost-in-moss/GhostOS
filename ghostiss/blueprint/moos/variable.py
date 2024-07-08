from typing import Any, Optional, List, Union, Type, TypedDict, Tuple
from abc import ABC, abstractmethod
import enum
import inspect
from ghostiss.container import Container, Provider, CONTRACT
from pydantic import BaseModel

ModelType = Union[BaseModel, TypedDict]


class Descriptive(ABC):

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass


class VarKind(str, enum.Enum):
    # --- 实例类型 --- #
    VALUE = "value"
    """变量类型是一个值. 可以的话输出它的描述. """

    LIBRARY = "library"
    """变量的类型是一个实例, 但 prompt 只输出它的 interface. 如果变量类型是类, 则从 DI 容器中取它的实例. """

    # --- types --- #

    CLASS = "class"
    """变量的类型是一个类, 可以在上下文中实例化. 需要描述 constructor & methods """

    ABSTRACT = "abstract"
    """变量的类型是一个类, 不能在上下文中实例化. 只会描述它的 public methods. """

    MODEL = "model"
    """变量的类型是一个 BaseModel/typed dict/其它, 它的源码对外展示, 但默认不展示相关方法? """

    CONTRACT = "contract"

    # --- callable --- #

    CALLER = "caller"
    """变量的类型是一个可以运行的函数. 可以是 function 或者 method. """

    def is_type(self) -> bool:
        pass

    def is_attr(self) -> bool:
        pass

    def is_model_type(self) -> bool:
        pass

    def is_contract_type(self) -> bool:
        pass

    def is_caller(self) -> bool:
        pass

    def is_property(self) -> bool:
        pass

    def is_lib(self) -> bool:
        pass


class Var(ABC):
    """
    一个可以被 LaMOS 理解并加载的变量.
    """

    @abstractmethod
    def value(self, container: Container) -> Any:
        """
        真实的值.
        """
        pass

    @abstractmethod
    def desc(self) -> Optional[str]:
        """
        变量的描述.
        """
        pass

    @abstractmethod
    def is_type(self) -> bool:
        pass

    @abstractmethod
    def is_caller(self) -> bool:
        pass

    @abstractmethod
    def implements(self) -> Optional[type]:
        """
        描述变量类型的 type.
        这个 type 需要在上下文中被介绍.
        class 类型的 var 不会有 type.
        """
        pass

    @abstractmethod
    def import_from(self) -> Optional[str]:
        pass

    @abstractmethod
    def code_prompt(self) -> Optional[str]:
        """
        是否有自定义的 prompt, 这样就不用生成了.
        对于变量而言, prompt 应该是初始化的表达式.
        对于类型而言, prompt 则是对外提示的源码.
        """
        pass


class ClassVar(Var):
    """
    输出一个类的类型变量.
    """

    def __init__(
            self, *,
            cls: type,
            alias: Optional[str] = None,
            doc: Optional[str] = None,
            module: Optional[str] = None,
            related_types: Optional[List[type]] = None,
            code_prompt: Optional[str] = None,
    ):
        if not inspect.isclass(cls):
            raise TypeError('cls is not a class')
        self._cls = cls
        self._alias = alias
        self._doc = doc
        self._module = module
        self._code_prompt = code_prompt
        self._related_types = related_types

    def name(self) -> str:
        if self._alias is None:
            return self._cls.__name__
        return self._alias

    def desc(self) -> Optional[str]:
        return self._doc

    def kind(self) -> VarKind:
        return VarKind.CLASS

    def implements(self) -> Optional[type]:
        # class 类型的变量, 不输出额外类型.
        return None

    def relate_types(self) -> Optional[List[implements]]:
        return self._related_types

    def value(self, container: Container) -> Any:
        return self._cls

    def module(self) -> Optional[str]:
        if self._module is None:
            return self._cls.__module__
        return self._module

    def module_val_name(self) -> Optional[str]:
        if self._module is None:
            return self._cls.__name__
        return self.name()

    def code_prompt(self) -> Optional[str]:
        return self._code_prompt


class ProviderVar(Var):
    """
    通过 provider 提供一个变量.
    """

    def __init__(
            self, *,
            provider: Provider,
            desc: Optional[str] = None,
            alias: Optional[str] = None,
            module: Optional[str] = None,
            related_types: Optional[List[type]] = None,
    ):
        self._provider = provider
        self._desc = desc
        self._alias = alias
        self._module = module
        self._related_types = related_types

    def name(self) -> str:
        if self._alias is not None:
            return self._alias
        return self._provider.contract().__name__

    def desc(self) -> Optional[str]:
        return self._desc

    def implements(self) -> type:
        return self._provider.contract()

    def kind(self) -> VarKind:
        return VarKind.LIBRARY

    def value(self, container: Container) -> Any:
        resolved = self._provider.factory(container)
        if resolved is None:
            # todo: 完善异常体系.
            raise RuntimeError("cannot resolve provider")
        return resolved

    def module(self) -> Optional[str]:
        if self._module:
            return self._module
        return self.implements().__module__

    def module_val_name(self) -> Optional[str]:
        if self._module:
            return self.name()
        return self.implements().__name__

    def code_prompt(self) -> Optional[str]:
        return None

    def relate_types(self) -> Optional[List[implements]]:
        return self._related_types


class ContractVar(Var):

    def __init__(
            self,
            *,
            contract: Type[CONTRACT],
            alias: Optional[str] = None,
            desc: Optional[str] = None,
            related_types: Optional[List[type]] = None,
            module: Optional[str] = None,
    ):
        self._contract = contract
        self._alias = alias
        self._desc = desc
        self._related_types = related_types
        self._module = module

    def desc(self) -> Optional[str]:
        return self._desc

    def kind(self) -> VarKind:
        return VarKind.LIBRARY

    def implements(self) -> Type[CONTRACT]:
        return self._contract

    def value(self, container: Container) -> Any:
        contract = self._contract
        return container.force_fetch(contract)

    def relate_types(self) -> Optional[List[implements]]:
        return self._related_types

    def module(self) -> Optional[str]:
        if self._module:
            return self._module
        return self.implements().__module__

    def module_val_name(self) -> Optional[str]:
        if self._alias:
            return self._alias
        return self.implements().__name__

    def code_prompt(self) -> Optional[str]:
        return None


class LibraryVar(Var):

    def __init__(
            self, *,
            name: str,
            ins: CONTRACT,
            type_: Type[CONTRACT],
            desc: Optional[str] = None,
            related_types: Optional[List[type]] = None,
            module: Optional[str] = None,
    ):
        self._ins = ins
        self._type = type_
        self._name = name
        self._desc = desc
        self._related_types = related_types
        self._module = module

    def name(self) -> str:
        return self._name

    def desc(self) -> Optional[str]:
        return self._desc

    def kind(self) -> VarKind:
        return VarKind.LIBRARY

    def implements(self) -> Optional[Type[CONTRACT]]:
        if self._type is not None:
            return self._type
        return type(self._ins)

    def value(self, container: Container) -> Any:
        return self._ins

    def relate_types(self) -> Optional[List[implements]]:
        return self._related_types

    def module(self) -> Optional[str]:
        if self._module:
            return self._module
        return type(self._ins).__module__

    def module_val_name(self) -> Optional[str]:
        return self._name

    def code_prompt(self) -> Optional[str]:
        return None


class Variable:
    """
    一个可以被 moos 处理的上下文变量.
    相当于 python 的对象, 给它添加了一些魔法变量.
    """

    def __init__(
            self, *,
            kind: VarKind,
            value: Any,
            description: Optional[str] = None,
            types: Optional[List[type]] = None,
            module: Optional[str] = None,
            module_val_name: Optional[str] = None,
            code_prompt: Optional[str] = None,
    ):
        self.kind: VarKind = kind
        """变量的基本类型."""

        self.value: Any = value
        """变量的真值."""

        self.description: Optional[str] = description
        """变量如果是一个值, 这里是值的描述. """

        self.types: Optional[List[type]] = types
        """声明变量所属的类型. 相同类型的变量会强调它的归属."""

        self.module: Optional[str] = module
        """引入变量的模块. """

        self.module_val_name: Optional[str] = module_val_name
        """从模块的变量名引入变量. """

        self.code_prompt: Optional[str] = code_prompt


def attr(*, val: Any, desc: Optional[str] = None, type_hint: Optional[type] = None) -> Var:
    pass


def lib(*, val: Any, contract: Optional[type] = None) -> Var:
    pass


def model(*, val: Any) -> Var:
    pass


def caller(*, val: Any) -> Var:
    pass
