from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Union
from pydantic import BaseModel, Field
from ghostos.helpers import generate_import_path
from typing_extensions import Protocol
from types import FunctionType
import inspect

__all__ = [
    'Descriptive',
    'Identifier', 'Identifiable', 'IdentifiableClass', 'identify_class', 'identify_class_id',
    'PromptAble', 'PromptAbleClass'
]


class Descriptive(ABC):

    @abstractmethod
    def get_description(self) -> str:
        pass


class Identifier(BaseModel):
    id: str = Field(default="", description="Unique identifier")
    name: str = Field(default="", description="Name of the object")
    description: str = Field(default="", description="Description of the object")
    kind: Optional[str] = Field(default=None, description="Kind of the object")


class Identifiable(ABC):
    """
    描述一个可识别的对象.
    """

    @abstractmethod
    def identifier(self) -> Identifier:
        pass


class IdentifiableProtocol(Protocol):
    id: Optional[str]
    name: str
    description: str


class IdentifiableClass(ABC):

    @classmethod
    @abstractmethod
    def class_identifier(cls) -> Identifier:
        pass


def identify_class(cls: type) -> Identifier:
    """
    一个默认的用来描述类的方法.
    :param cls: 目标类.
    :return: 返回一个 identifier.
    """
    if issubclass(cls, IdentifiableClass):
        return cls.class_identifier()
    id_ = identify_class_id(cls)
    name = cls.__name__
    desc = cls.__doc__
    return Identifier(
        id=id_,
        name=name,
        description=desc,
        kind="class",
    )


def identify_class_id(cls: type) -> str:
    return generate_import_path(cls)


def get_identifier(value: Any) -> Optional[Identifier]:
    if isinstance(value, Identifier):
        return value
    if isinstance(value, Identifiable):
        return value.identifier()
    if isinstance(value, IdentifiableClass):
        return value.class_identifier()
    if inspect.isfunction(value):
        return Identifier(
            id=generate_import_path(value),
            name=value.__name__,
            description=value.__doc__,
            kind="function",
        )
    if inspect.ismethod(value):
        return Identifier(
            id=generate_import_path(value.__class__) + ":" + value.__name__,
            name=value.__name__,
            description=value.__doc__,
            kind="method",
        )
    if isinstance(value, type):
        return identify_class(value)
    if isinstance(value, Dict) and "name" in value and "description" in value:
        return Identifier(
            id=value.get("id", None),
            name=value["name"],
            description=value["description"],
            kind=str(type(value)),
        )
    if isinstance(value, object) and hasattr(value, 'name') and hasattr(value, 'description'):
        return Identifier(
            id=getattr(value, 'id', None),
            name=getattr(value, 'name'),
            description=getattr(value, 'description'),
            kind=str(type(value)),
        )
    return None


IDAble = Union[Identifier, Identifiable, IdentifiableClass, type, FunctionType, IdentifiableProtocol]


class PromptAble(ABC):
    """
    拥有 __prompt__ 方法的类.
    这里只是一个示范, 并不需要真正继承这个类, 只需要有 __prompt__ 方法或属性.
    """

    @abstractmethod
    def __prompt__(self) -> str:
        pass


class PromptAbleClass(ABC):

    @classmethod
    @abstractmethod
    def __class_prompt__(cls) -> str:
        pass
