from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, TypedDict
from typing_extensions import Required
from ghostiss.container import Container

__all__ = [
    'Entity', 'EntityMeta',
    'ENTITY_TYPE', 'InContainerEntity',
    'EntityClass', 'EntityFactory',
]


class EntityMeta(TypedDict, total=False):
    """
    meta-data that could:
    1. transport as dict data, weak type-hint
    2. be used to regenerate [Meta]
    """

    id: Optional[str]
    """ if id given, the meta is able to register and fetch from repository"""

    type: Required[str]
    """ different type of entity use different EntityFactory to initialize from meta"""

    driver: Optional[str]
    """ optional for EntityFactory to choose driver """

    data: Required[dict]
    """ use dict to restore the serializable data"""


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
    def new_entity(cls, meta: EntityMeta) -> Optional["EntityClass"]:
        pass


class InContainerEntity(Entity, ABC):

    @classmethod
    @abstractmethod
    def new_entity(cls, container: Container, meta: EntityMeta) -> Optional["InContainerEntity"]:
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
