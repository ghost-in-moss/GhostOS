from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Union
from pydantic import BaseModel, Field


class MetaData(BaseModel):
    """
    meta-data that could:
    1. transport as dict data, weak type-hint
    2. be used to regenerate [Meta]
    """

    id: str = Field(description="meta id")
    kind: str = Field(description="")
    clazz: str = Field(description="")
    data: dict = Field(default_factory=dict, description="meta data for create a meta object")


class Meta(ABC):
    """
    meta is a strong type-hint class that can generate meta-data to transport
    """

    @abstractmethod
    def to_meta_data(self) -> MetaData:
        pass


M = TypeVar("M", bound=Meta)


class MetaObject(Generic[M], ABC):

    @abstractmethod
    def get_meta(self) -> M:
        pass


class MetaClass(Generic[M], ABC):

    @abstractmethod
    def meta_kind(self) -> str:
        pass

    @abstractmethod
    def meta_class(self) -> str:
        pass

    @abstractmethod
    def meta_new(self, meta_data: MetaData) -> M:
        pass


C = TypeVar("C", bound=MetaClass)


class MetaFactory(Generic[C], ABC):

    @abstractmethod
    def kind(self) -> str:
        pass

    @abstractmethod
    def factory(self, meta_data: MetaData) -> Optional[C]:
        pass


class MetaRepository(Generic[M], ABC):
    """
    save meta object.
    """

    @abstractmethod
    def kind(self) -> str:
        pass

    @abstractmethod
    def register_class(self, meta_class: MetaClass[M]) -> None:
        pass

    @abstractmethod
    def get_class(self, clazz_name: str) -> Optional[MetaClass[M]]:
        pass

    @abstractmethod
    def register_meta(self, meta: Union[M, MetaData]) -> None:
        pass

    @abstractmethod
    def get_meta(self, meta_id: str) -> Optional[M]:
        pass
