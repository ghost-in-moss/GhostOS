from typing import Optional, TypedDict, Callable, Type, TypeVar
from types import ModuleType
from abc import ABC, abstractmethod

from typing_extensions import Required
from ghostos.helpers import generate_import_path, import_from_path
from pydantic import BaseModel

__all__ = [
    'Entity', 'EntityMeta',
    'EntityFactory',
    'ModelEntity',
    'EntityFactoryImpl',
    'model_to_entity_meta',
]


class EntityMeta(TypedDict, total=False):
    """
    meta-data that could:
    1. transport as dict data, weak type-hint
    2. be used to regenerate [Meta]
    """

    type: Required[str]
    """ different type of entity use different EntityFactory to initialize from meta"""

    data: Required[dict]
    """ use dict to restore the serializable data"""


def model_to_entity_meta(model: BaseModel) -> EntityMeta:
    type_ = generate_import_path(type(model))
    data = model.model_dump(exclude_defaults=True)
    return EntityMeta(
        type=type_,
        data=data,
    )


class Entity(ABC):
    """
    meta is a strong type-hint class that can generate meta-data to transport
    """

    @abstractmethod
    def to_entity_data(self) -> dict:
        pass

    def to_entity_meta(self) -> EntityMeta:
        """
        generate transportable meta-data
        """
        type_ = generate_import_path(self.__class__)
        data = self.to_entity_data()
        return EntityMeta(type=type_, data=data)

    @classmethod
    @abstractmethod
    def from_entity_meta(cls, factory: "EntityFactory", meta: EntityMeta) -> "Entity":
        pass


class ModelEntity(BaseModel, Entity, ABC):
    """
    Entity based on pydantic.BaseModel
    """

    def to_entity_data(self) -> dict:
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_entity_meta(cls, factory: "EntityFactory", meta: EntityMeta) -> "ModelEntity":
        return cls(**meta['data'])


E = TypeVar('E', bound=Entity)


class EntityFactory(ABC):
    """
    Factory for Entity
    """

    @abstractmethod
    def new_entity(self, meta_data: EntityMeta) -> Optional[Entity]:
        """
        try to new an entity from meta-data
        """
        pass

    @abstractmethod
    def force_new_entity(self, meta_data: EntityMeta, expect: Type[E]) -> E:
        """
        :param meta_data:
        :param expect: expect entity type
        :return: EntityType instance
        :exception: TypeError
        """
        pass


class EntityFactoryImpl(EntityFactory):

    def __init__(self, importer: Optional[Callable[[str], ModuleType]] = None):
        self._importer = importer

    def new_entity(self, meta_data: EntityMeta) -> Optional[Entity]:
        type_ = meta_data['type']
        cls = import_from_path(type_, self._importer)
        if cls is None:
            return None
        if not issubclass(cls, Entity):
            raise TypeError(f"Entity type {type_} does not inherit from Entity")
        return cls.from_entity_meta(self, meta_data)

    def force_new_entity(self, meta_data: EntityMeta, expect: Type[E]) -> E:
        entity = self.new_entity(meta_data)
        if entity is None:
            raise TypeError(f"meta data {meta_data['type']} can not be instanced")
        if not isinstance(entity, expect):
            raise TypeError(f"Entity type {meta_data['type']} does not match {expect}")
        return entity
