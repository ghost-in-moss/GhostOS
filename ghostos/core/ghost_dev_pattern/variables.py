from abc import ABC, abstractmethod
from typing import Protocol, Self, Optional, Union, Type, TypeVar, Any, Dict, TypedDict
from typing_extensions import Required

T = TypeVar("T")


class VarPtr(TypedDict):
    vid: Required[str]
    type: Required[str]
    desc: Optional[str]


class Variables(ABC):

    @abstractmethod
    def get(self, vid: str, expect: Optional[Type[T]] = None, force: bool = False) -> Optional[T]:
        pass

    @abstractmethod
    def save(self, value: Any, vid: Optional[str] = None) -> VarPtr:
        pass
