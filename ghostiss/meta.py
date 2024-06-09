from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Type, ClassVar, Union
from pydantic import BaseModel, Field


class MetaData(BaseModel):
    """
    meta-data that could:
    1. transport as dict data, weak type-hint
    2. be used to regenerate [Meta]
    """

    id: str = Field(description="meta id")
    kind: str = Field(description="")
    data: dict = Field(default_factory=dict, description="meta data for create a meta object")


class Meta(ABC):
    """
    meta is a strong type-hint class that can generate meta-data to transport
    """

    @abstractmethod
    def meta_kind(self) -> str:
        pass

    @abstractmethod
    def get_meta_data(self) -> MetaData:
        """
        generate transportable meta-data
        """
        pass


class MetaClass(Meta, ABC):

    @classmethod
    @abstractmethod
    def meta_kind(cls) -> str:
        pass

    @abstractmethod
    def meta_id(self) -> str:
        pass

    @classmethod
    @abstractmethod
    def meta_make(cls, meta_data: MetaData) -> "MetaClass":
        pass


class BaseMetaClass(MetaClass, BaseModel, ABC):
    """
    基于 pydantic 实现的 MetaClass.
    """

    def get_meta_data(self) -> MetaData:
        return MetaData(
            id=self.meta_id(),
            kind=self.meta_kind(),
            data=self.model_dump(),
        )

    @classmethod
    def meta_make(cls, meta_data: MetaData) -> "MetaClass":
        return cls(**meta_data.model_dump())


T = TypeVar("T", bound=MetaClass)


class MetaClassLoader(Generic[T]):

    def __init__(self, kinds: List[Type[T]]):
        self.kinds: Dict[str, Type[T]] = {}
        for kind in kinds:
            self.register_meta_class(kind)

    def load_meta_class(self, clazz: str) -> Optional[Type[T]]:
        return self.kinds.get(clazz, None)

    def register_meta_class(self, clazz: Type[T]) -> None:
        self.kinds[clazz.meta_class()] = clazz

    def force_load_class(self, clazz: str) -> Type[T]:
        load = self.load_meta_class(clazz)
        if load is None:
            raise NotImplemented("Meta class {} not found".format(clazz))
        return load

    def meta_make(self, meta_data: MetaData) -> Optional[T]:
        clazz = self.load_meta_class(meta_data.kind)
        if clazz is None:
            return None
        return clazz.meta_make(meta_data)


M = TypeVar("M", bound=Meta)


class MetaObject(Generic[M], ABC):

    @abstractmethod
    def get_meta(self) -> M:
        pass


META_TYPE = TypeVar('META_TYPE', Meta, MetaObject)


class MetaMaker(Generic[META_TYPE], ABC):
    """
    simple and stupid 的命名.
    """

    @abstractmethod
    def meta_kind(self) -> str:
        pass

    @abstractmethod
    def meta_make(self, meta_data: MetaData) -> META_TYPE:
        """
        :raise NotImplemented: when meta kind is not implemented
        """
        pass


class MetaFactory(Generic[META_TYPE], ABC):

    @abstractmethod
    def register(self, maker: Union[MetaMaker[META_TYPE], Type[MetaClass]]) -> None:
        pass

    @abstractmethod
    def get_factory(self, meta_kind: str) -> Optional[MetaMaker[META_TYPE], Type[MetaClass]]:
        pass

    @abstractmethod
    def meta_make(self, meta_data: MetaData) -> Optional[META_TYPE]:
        pass

    def force_meta_make(self, meta_data: MetaData) -> META_TYPE:
        mind = self.meta_make(meta_data)
        if mind is None:
            raise NotImplemented("todo")
        return mind

    @abstractmethod
    def register_meta(self, data: Union[MetaData, Meta, MetaObject]) -> None:
        pass

    @abstractmethod
    def get(self, meta_id: str) -> Optional[META_TYPE]:
        pass

    @abstractmethod
    def has(self, mind_kind: str) -> bool:
        pass
