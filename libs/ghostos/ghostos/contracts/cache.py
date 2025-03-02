from __future__ import annotations

from typing import Optional
from abc import ABCMeta, abstractmethod


class Cache(metaclass=ABCMeta):
    """
    通用的 cache 封装.
    """

    @abstractmethod
    def lock(self, key: str, overdue: int = 0) -> bool:
        pass

    @abstractmethod
    def unlock(self, key: str) -> bool:
        pass

    @abstractmethod
    def set(self, key: str, val: str, exp: int = 0) -> bool:
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    def expire(self, key: str, exp: int) -> bool:
        pass

    @abstractmethod
    def set_member(self, key: str, member: str, value: str) -> bool:
        pass

    @abstractmethod
    def get_member(self, key: str, member: str) -> Optional[str]:
        pass

    def remove_member(self, key: str, *member: str) -> int:
        pass

    @abstractmethod
    def remove(self, *keys: str) -> int:
        pass
