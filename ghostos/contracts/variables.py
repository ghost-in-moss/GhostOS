from typing import AnyStr, TypedDict, Required, Union, Dict, List, TypeVar, Type, Optional
from typing_extensions import Self
from abc import ABC, abstractmethod
from pydantic import BaseModel


class VarPtr(TypedDict):
    id: Required[str]
    kind: Required[str]


class VarData(TypedDict):
    id: Required[str]
    kind: Required[str]
    data: Required[bytes]


class Var(ABC):
    @abstractmethod
    def marshal(self) -> bytes:
        pass

    @classmethod
    @abstractmethod
    def unmarshal(cls, value: bytes) -> Self:
        pass

    def ptr(self) -> VarPtr:
        pass


V = TypeVar('V', Var, BaseModel, Dict, List, str, int, float)


class Variables(ABC):

    @abstractmethod
    def save(self, v: Union[Var, BaseModel, dict, list, str, int, float]) -> VarPtr:
        pass

    @abstractmethod
    def load(self, vid: str, wrapper: Type[V]) -> Optional[V]:
        pass


class ModelVar(Var):

    def __init__(self, model: BaseModel):
        pass


class PickleVar(Var):
    pass
