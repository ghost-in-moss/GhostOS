from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Type, ClassVar, Union, TypedDict
from typing_extensions import Required
from pydantic import BaseModel, Field


class EntityMeta(TypedDict, total=False):
    """
    meta-data that could:
    1. transport as dict data, weak type-hint
    2. be used to regenerate [Meta]
    """

    id: Optional[str]
    type: Required[str]
    data: Required[dict]


class Entity(ABC):
    """
    meta is a strong type-hint class that can generate meta-data to transport
    """

    @abstractmethod
    def to_entity_meta(self) -> EntityMeta:
        """
        generate transportable meta-data
        """
        pass


class EntityClass(Entity, ABC):

    @classmethod
    @abstractmethod
    def entity_type(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def new_entity(cls, meta: EntityMeta) -> Optional["EntityClass"]:
        pass


ENTITY_TYPE = TypeVar("ENTITY_TYPE", bound=Entity)


class EntityFactory(Generic[ENTITY_TYPE], ABC):

    @abstractmethod
    def new_entity(self, meta_data: EntityMeta) -> Optional[ENTITY_TYPE]:
        pass

    def force_new_entity(self, meta_data: EntityMeta) -> ENTITY_TYPE:
        mind = self.new_entity(meta_data)
        if mind is None:
            raise NotImplemented("todo")
        return mind
