from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Type, ClassVar, Union
from pydantic import BaseModel, Field


class Normalized(BaseModel):
    """
    meta-data that could:
    1. transport as dict data, weak type-hint
    2. be used to regenerate [Meta]
    """

    id: str = Field(description="meta id")
    kind: str = Field(description="")
    data: dict = Field(default_factory=dict, description="meta data for create a meta object")


class Entity(ABC):
    """
    meta is a strong type-hint class that can generate meta-data to transport
    """

    @abstractmethod
    def entity_kind(self) -> str:
        pass

    @abstractmethod
    def normalize(self) -> Normalized:
        """
        generate transportable meta-data
        """
        pass


class EntityClass(Entity, ABC):

    @classmethod
    @abstractmethod
    def entity_kind(cls) -> str:
        pass

    @abstractmethod
    def entity_id(self) -> str:
        pass

    @classmethod
    @abstractmethod
    def new_entity(cls, meta_data: Normalized) -> "EntityClass":
        pass


class BaseEntityClass(EntityClass, BaseModel, ABC):
    """
    基于 pydantic 实现的 MetaClass.
    """

    def normalize(self) -> Normalized:
        return Normalized(
            id=self.entity_id(),
            kind=self.entity_kind(),
            data=self.model_dump(),
        )

    @classmethod
    def new_entity(cls, meta_data: Normalized) -> "EntityClass":
        return cls(**meta_data.model_dump())


ENTITY_CLASS_TYPE = TypeVar("ENTITY_CLASS_TYPE", bound=EntityClass)


class EntityClassLoader(Generic[ENTITY_CLASS_TYPE]):

    def __init__(self, kinds: List[Type[ENTITY_CLASS_TYPE]]):
        self.kinds: Dict[str, Type[ENTITY_CLASS_TYPE]] = {}
        for kind in kinds:
            self.add_entity_class(kind)

    def get_entity_class(self, clazz: str) -> Optional[Type[ENTITY_CLASS_TYPE]]:
        return self.kinds.get(clazz, None)

    def add_entity_class(self, clazz: Type[ENTITY_CLASS_TYPE]) -> None:
        self.kinds[clazz.meta_class()] = clazz

    def force_get_entity_class(self, clazz: str) -> Type[ENTITY_CLASS_TYPE]:
        load = self.get_entity_class(clazz)
        if load is None:
            raise NotImplemented("Meta class {} not found".format(clazz))
        return load

    def new_entity(self, meta_data: Normalized) -> Optional[ENTITY_CLASS_TYPE]:
        clazz = self.get_entity_class(meta_data.kind)
        if clazz is None:
            return None
        return clazz.new_entity(meta_data)


ENTITY_TYPE = TypeVar("ENTITY_TYPE", bound=Entity)


class EntityDriver(Generic[ENTITY_TYPE], ABC):

    @abstractmethod
    def entity_kind(self) -> str:
        pass

    @abstractmethod
    def new_entity(self, data: Normalized) -> ENTITY_TYPE:
        pass


class MetaFactory(Generic[ENTITY_TYPE], ABC):

    @abstractmethod
    def add_driver(self, maker: EntityDriver[ENTITY_TYPE]) -> None:
        pass

    @abstractmethod
    def get_driver(self, meta_kind: str) -> Optional[EntityDriver[ENTITY_TYPE]]:
        pass

    def new_entity(self, meta_data: Normalized) -> Optional[ENTITY_TYPE]:
        maker = self.get_driver(meta_data.kind)
        if maker is None:
            return None
        return maker.new_entity(meta_data)

    def force_new_entity(self, meta_data: Normalized) -> ENTITY_TYPE:
        mind = self.new_entity(meta_data)
        if mind is None:
            raise NotImplemented("todo")
        return mind
