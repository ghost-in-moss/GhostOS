from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Union, Callable, Any
from pydantic import BaseModel, Field
from ghostos_common.helpers import generate_import_path
from typing_extensions import Protocol
import inspect

__all__ = [
    'get_identifier', 'try_get_identifier',
    'identify_class',
    'identify_class_id',

    'Identifier', 'Identifiable',
    'Identical', 'IdenticalClass',
    'IdenticalObject',

]


def get_identifier(value: Any) -> Identifier:
    """
    get identifier or not from any value
    """
    id_ = try_get_identifier(value)
    if id_ is None:
        raise AttributeError(f'{value} is not an identifier')
    return id_


def try_get_identifier(value: Any, throw: bool = False) -> Union[Identifier, None]:
    try:
        if value is None:
            return None
        # identifier it self
        if isinstance(value, Identifier):
            return value
        # explicit identifiable object
        elif isinstance(value, Identical):
            return value.__identifier__()
        # explicit identifiable class
        elif issubclass(value, IdenticalClass):
            return value.class_identifier()
        # function is always identifiable
        elif inspect.isfunction(value):
            return Identifier(
                id=generate_import_path(value),
                name=value.__name__,
                description=value.__doc__,
            )
        # method just like function
        elif inspect.ismethod(value):
            return Identifier(
                id=generate_import_path(value.__class__) + ":" + value.__name__,
                name=value.__name__,
                description=value.__doc__,
            )
        # class is special at runtime.
        # notice the id of a class is alternative at different project due to python import by relative path.
        elif isinstance(value, type):
            return identify_class(value)
        # a dict
        elif isinstance(value, Dict) and "name" in value and "description" in value:
            return Identifier(
                id=value.get("id", None),
                name=value["name"],
                description=value["description"],
            )
        elif hasattr(value, "__identifier__"):
            identifier = getattr(value, "identifier")
            if isinstance(identifier, Identifier):
                return identifier
            elif isinstance(identifier, Callable):
                return identifier()

        elif hasattr(value, 'name') and hasattr(value, 'description'):
            return Identifier(
                id=getattr(value, 'id', None),
                name=getattr(value, 'name'),
                description=getattr(value, 'description'),
            )
        return None
    except Exception:
        if throw:
            raise
        return None


class Identifier(BaseModel):
    """
    a simplest model identify an object
    """
    id: Optional[str] = Field(default=None, description="Unique id")
    name: str = Field(
        default="",
        description="Name of the object, name has it meaning only for the subject who named it",
    )
    description: str = Field(default="", description="Description of the object")

    def match_keyword(self, keyword: str) -> bool:
        keyword = keyword.strip()
        if not keyword:
            return True
        return (
                keyword.lower() in self.name.lower()
                or keyword.lower() in self.description.lower()
                or keyword.lower() in self.id.lower()
        )


class Identical(ABC):
    """
    abstract class that identifiable class can extend it.
    """

    @abstractmethod
    def __identifier__(self) -> Identifier:
        pass


class IdenticalObject(Protocol):
    """
    less invasive way to describe an identifiable object.
    when we need to hide the complexity of a class to someone, especially the AI model,
    we need to use protocol to do implicit implementation sometimes. duck type is useful.
    """

    @abstractmethod
    def __identifier__(self) -> Identifier:
        pass


class IdenticalClass(ABC):
    """
    class is identifiable, but sometimes we need to specific the identifier.
    """

    @classmethod
    @abstractmethod
    def class_identifier(cls) -> Identifier:
        pass


Identifiable = Union[Identical, IdenticalObject]


def identify_class(cls: type) -> Identifier:
    """
    一个默认的用来描述类的方法.
    :param cls: 目标类.
    :return: 返回一个 identifier.
    """
    if issubclass(cls, IdenticalClass):
        return cls.class_identifier()
    id_ = identify_class_id(cls)
    name = cls.__name__
    desc = cls.__doc__
    return Identifier(
        id=id_,
        name=name,
        description=desc or "",
    )


def identify_class_id(cls: type) -> str:
    return generate_import_path(cls)
