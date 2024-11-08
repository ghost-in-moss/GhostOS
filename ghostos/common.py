from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Union, Callable, Any, TypedDict, Required, Self, TypeVar, Type
from types import ModuleType
from pydantic import BaseModel, Field
from ghostos.helpers import generate_import_path, import_from_path
from typing_extensions import Protocol
import inspect
import pickle

__all__ = [
    'get_identifier',
    'Identifier', 'Identifiable',

    'Identical', 'IdenticalClass',
    'identify_class', 'identify_class_id',
    'IdenticalObject',

    'to_entity_meta', 'from_entity_meta', 'get_entity',
    'EntityMeta', 'Entity', 'EntityType',

    'get_defined_prompt',
    'Prompter', 'PrompterClass',

]


def get_defined_prompt(value: Any) -> Union[str, None]:
    if value is None:
        return None
    elif isinstance(value, Prompter):
        return value.__prompt__()
    elif issubclass(value, PrompterClass):
        return value.__class_prompt__()

    elif isinstance(value, type):
        # class without __class_prompt__ is not defined as prompter
        if hasattr(value, "__class_prompt___"):
            return getattr(value, "__class_prompt___")()

    elif hasattr(value, "__prompter__"):
        prompter = getattr(value, "__prompter__")
        if prompter.__self__ is not None:
            return prompter()
    elif isinstance(value, ModuleType) and '__prompt__' in value.__dict__:
        prompter = value.__dict__['__prompt__']
        return prompter()
    return None


def get_identifier(value: Any, throw: bool = False) -> Union[Identifier, None]:
    """
    get identifier or not from any value
    """
    try:
        if value is None:
            return None
        # identifier it self
        if isinstance(value, Identifier):
            return value
        # explicit identifiable object
        elif isinstance(value, Identical):
            return value.identifier()
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
    def identifier(self) -> Identifier:
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
        description=desc,
        kind="class",
    )


def identify_class_id(cls: type) -> str:
    return generate_import_path(cls)


# ---- prompt ---- #


class Prompter(ABC):
    """
    拥有 __prompt__ 方法的类.
    这里只是一个示范, 并不需要真正继承这个类, 只需要有 __prompt__ 方法或属性.
    """

    @abstractmethod
    def __prompt__(self) -> str:
        pass


class PromptAbleObj(Protocol):
    @abstractmethod
    def __prompt__(self) -> str:
        pass


class PrompterClass(ABC):

    @classmethod
    @abstractmethod
    def __class_prompt__(cls) -> str:
        pass


class PromptAbleClass(Protocol):

    @classmethod
    @abstractmethod
    def __class_prompt__(cls) -> str:
        pass


PromptAble = Union[PromptAbleObj, PromptAbleClass]


# ---- entity ---- #

class Entity(Protocol):

    @abstractmethod
    def __to_entity_meta__(self) -> EntityMeta:
        pass

    @classmethod
    @abstractmethod
    def __from_entity_meta__(cls, meta: EntityMeta) -> Self:
        pass


class EntityMeta(TypedDict):
    """
    I want python has an official way to marshal and unmarshal any instance and make it readable if allowed.
    I found so many package-level implements like various kinds of Serializable etc.

    So, I develop EntityMeta as a wrapper for any kind.
    The EntityType will grow bigger with more marshaller, but do not affect who (me) is using the EntityMeta.

    One day I can replace it with any better way inside the functions (but in-compatible)
    """
    type: Required[str]
    content: Required[bytes]


EntityType = Union[Entity, EntityMeta, BaseModel]


def to_entity_meta(value: Union[EntityType, Any]) -> EntityMeta:
    if isinstance(value, EntityMeta):
        return value
    elif hasattr(value, '__to_entity_meta__'):
        return getattr(value, '__to_entity_meta__')()
    elif isinstance(value, BaseModel):
        return EntityMeta(
            type=generate_import_path(value.__class__),
            content=value.model_dump_json(exclude_defaults=True).encode(),
        )
    elif inspect.isfunction(value):
        return EntityMeta(
            type=generate_import_path(value),
            content=bytes(),
        )
    else:
        content = pickle.dumps(value)
        return EntityMeta(
            type="pickle",
            content=content,
        )


T = TypeVar("T")


def get_entity(meta: EntityMeta, expect: Type[T]) -> T:
    entity = from_entity_meta(meta)
    if not isinstance(entity, expect):
        raise TypeError(f"Expected entity type {expect} but got {type(entity)}")
    return entity


def from_entity_meta(meta: EntityMeta) -> Any:
    unmarshal_type = meta['type']
    if unmarshal_type == 'pickle':
        return pickle.loads(meta['content'])

    # raise if import error
    cls = import_from_path(unmarshal_type)

    if issubclass(cls, EntityMeta):
        return meta
    elif inspect.isfunction(cls):
        return cls
    # method is prior
    elif hasattr(cls, "__from_entity_meta__"):
        return getattr(cls, "__from_entity_meta__")(meta)

    elif issubclass(cls, BaseModel):
        data = json.loads(meta["content"])
        return cls(**data)

    raise TypeError(f"unsupported entity meta type: {unmarshal_type}")
