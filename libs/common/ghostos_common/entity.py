from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Union, Any, TypeVar, Type, Optional, Protocol
from typing_extensions import Required, Self, TypedDict
from types import ModuleType
from pydantic import BaseModel
from ghostos_common.helpers import generate_import_path, import_from_path, parse_import_path_module_and_attr_name
import inspect
import pickle
import base64
import yaml

__all__ = [

    'to_entity_meta', 'from_entity_meta', 'get_entity',
    'is_entity_type',
    'EntityMeta',
    'Entity', 'EntityType',
    'EntityClass', 'ModelEntity',

    'ModelEntityMeta',
    'to_entity_model_meta',
    'from_entity_model_meta',

]


class Entity(Protocol):

    @abstractmethod
    def __to_entity_meta__(self) -> EntityMeta:
        pass

    @classmethod
    @abstractmethod
    def __from_entity_meta__(cls, meta: EntityMeta) -> Self:
        pass


class EntityClass(ABC):

    @abstractmethod
    def __to_entity_meta__(self) -> EntityMeta:
        pass

    @classmethod
    @abstractmethod
    def __from_entity_meta__(cls, meta: EntityMeta) -> Self:
        pass


class ModelEntity(BaseModel, EntityClass, ABC):

    def __to_entity_meta__(self) -> EntityMeta:
        return EntityMeta(
            type=generate_import_path(self.__class__),
            content=self.model_dump_json(exclude_defaults=True),
        )

    @classmethod
    def __from_entity_meta__(cls, meta: EntityMeta) -> Self:
        data = json.loads(meta['content'])
        return cls(**data)


class EntityMeta(TypedDict):
    """
    I want python has an official way to marshal and unmarshal any instance and make it readable if allowed.
    I found so many package-level implements like various kinds of Serializable etc.

    So, I develop EntityMeta as a wrapper for any kind.
    The EntityType will grow bigger with more marshaller, but do not affect who (me) is using the EntityMeta.

    One day I can replace it with any better way inside the functions (but in-compatible)
    """
    type: Required[str]
    content: Required[str]


class ModelEntityMeta(TypedDict):
    type: Required[str]
    data: Required[dict]


EntityType = Union[Entity, EntityMeta, BaseModel]


def is_entity_type(value: Any) -> bool:
    return hasattr(value, '__to_entity_meta__')


def to_entity_model_meta(value: BaseModel) -> ModelEntityMeta:
    type_ = generate_import_path(type(value))
    data = value.model_dump(exclude_defaults=True)
    return ModelEntityMeta(type=type_, data=data)


def from_entity_model_meta(value: ModelEntityMeta) -> BaseModel:
    cls = import_from_path(value['type'])
    return cls(**value['data'])


def to_entity_meta(value: Union[EntityType, Any]) -> EntityMeta:
    if value is None:
        return EntityMeta(
            type="None",
            content="",
        )
    elif value is True or value is False:
        return EntityMeta(type="bool", content=str(value))
    elif isinstance(value, int):
        return EntityMeta(type="int", content=str(value))
    elif isinstance(value, str):
        return EntityMeta(type="str", content=str(value))
    elif isinstance(value, float):
        return EntityMeta(type="float", content=str(value))
    elif isinstance(value, list):
        content = yaml.safe_dump(value)
        return EntityMeta(type="list", content=content)
    elif isinstance(value, dict):
        content = yaml.safe_dump(value)
        return EntityMeta(type="dict", content=content)
    elif hasattr(value, '__to_entity_meta__'):
        return getattr(value, '__to_entity_meta__')()
    elif isinstance(value, BaseModel):
        return EntityMeta(
            type=generate_import_path(value.__class__),
            content=value.model_dump_json(exclude_defaults=True),
        )
    elif inspect.isfunction(value):
        return EntityMeta(
            type=generate_import_path(value),
            content="",
        )
    elif isinstance(value, BaseModel):
        type_ = generate_import_path(value.__class__)
        content = value.model_dump_json(exclude_defaults=True)
        return EntityMeta(type=type_, content=content)
    else:
        content_bytes = pickle.dumps(value)
        content = base64.encodebytes(content_bytes)
        return EntityMeta(
            type="pickle",
            content=content.decode(),
        )


T = TypeVar("T")


def get_entity(meta: EntityMeta, expect: Type[T]) -> T:
    if meta is None:
        raise ValueError("EntityMeta cannot be None")
    entity = from_entity_meta(meta)
    if not isinstance(entity, expect):
        raise TypeError(f"Expected entity type {expect} but got {type(entity)}")
    return entity


def from_entity_meta(meta: EntityMeta, module: Optional[ModuleType] = None) -> Any:
    if meta is None:
        return None
    unmarshal_type = meta['type']
    if unmarshal_type == "None":
        return None
    elif unmarshal_type == "int":
        return int(meta['content'])
    elif unmarshal_type == "str":
        return str(meta['content'])
    elif unmarshal_type == "bool":
        return meta['content'] == "True"
    elif unmarshal_type == "float":
        return float(meta['content'])
    elif unmarshal_type == "list" or unmarshal_type == "dict":
        return yaml.safe_load(meta['content'])
    elif unmarshal_type == 'pickle':
        content = meta['content']
        content_bytes = base64.decodebytes(content.encode())
        return pickle.loads(content_bytes)

    # raise if import error
    cls = None
    if module:
        module_name, local_name = parse_import_path_module_and_attr_name(unmarshal_type)
        if module_name == module.__name__:
            cls = module.__dict__[local_name]
    if cls is None:
        cls = import_from_path(unmarshal_type)

    if inspect.isfunction(cls):
        return cls
    # method is prior
    elif hasattr(cls, "__from_entity_meta__"):
        return getattr(cls, "__from_entity_meta__")(meta)

    elif issubclass(cls, BaseModel):
        data = json.loads(meta["content"])
        return cls(**data)

    raise TypeError(f"unsupported entity meta type: {unmarshal_type}")
