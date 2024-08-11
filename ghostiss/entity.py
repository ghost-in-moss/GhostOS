from abc import ABC, abstractmethod
from typing import Optional, TypedDict
from typing_extensions import Required
from ghostiss.helpers import generate_import_path, import_from_path
from pydantic import BaseModel

__all__ = [
    'Entity', 'EntityMeta',
    'EntityFactory',
    'ModelEntity', 'ModelEntityFactory',
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


class EntityFactory(ABC):

    @abstractmethod
    def new_entity(self, meta_data: EntityMeta) -> Optional[Entity]:
        pass

    def force_new_entity(self, meta_data: EntityMeta) -> Entity:
        mind = self.new_entity(meta_data)
        if mind is None:
            raise NotImplemented("todo")
        return mind


class ModelEntity(BaseModel, Entity, ABC):

    def to_entity_meta(self) -> EntityMeta:
        """
        """
        data = self.model_dump(exclude_none=True)
        cls = self.__class__
        type_ = generate_import_path(cls)
        # 默认没有 id 字段.
        return EntityMeta(
            type=type_,
            data=data,
        )


class ModelEntityFactory(EntityFactory):

    def new_entity(self, meta_data: EntityMeta) -> Optional[ModelEntity]:
        data_ = meta_data.get('data', {})
        type_ = meta_data.get('type', '')
        if not type_:
            return None
        cls = import_from_path(type_)
        if not issubclass(cls, ModelEntity):
            return None
        return cls(**data_)
