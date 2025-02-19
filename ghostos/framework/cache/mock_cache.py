from __future__ import annotations

import time
from typing import Dict, Type, Optional

from ghostos_container import Provider, Container
from ghostos.contracts.cache import Cache


class MockCache(Cache):
    __locker = set()
    __strings = {}
    __hash_map = {}
    __overdue: Dict[str, int] = {}

    def lock(self, key: str, overdue: int = 0) -> bool:
        if key in self.__locker and not self.__is_overdue(key):
            return False

        self.__locker.add(key)
        self.__set_overdue(key, overdue)
        return True

    def __set_overdue(self, key: str, overdue: int) -> None:
        if overdue <= 0:
            self.__overdue[key] = overdue
        else:
            self.__overdue[key] = int(time.time()) + overdue

    def __is_overdue(self, key: str) -> bool:
        if key not in self.__overdue:
            return False
        overdue = self.__overdue[key]
        if overdue <= 0:
            return False
        now = int(time.time())
        return overdue < now

    def unlock(self, key: str) -> bool:
        if key in self.__locker:
            self.__locker.remove(key)
            self.remove(key)
            return True
        return False

    def set(self, key: str, val: str, exp: int = 0) -> bool:
        self.__strings[key] = val
        self.__set_overdue(key, exp)
        return True

    def get(self, key: str) -> str | None:
        if self.__is_overdue(key):
            self.remove(key)
            return None
        return self.__strings.get(key, None)

    def expire(self, key: str, exp: int) -> bool:
        if key in self.__overdue:
            self.__set_overdue(key, exp)
            return True
        return False

    def set_member(self, key: str, member: str, value: str) -> bool:
        if key not in self.__hash_map:
            self.__hash_map[key] = {}
        self.__hash_map[key][member] = value
        return True

    def get_member(self, key: str, member: str) -> str | None:
        return self.__hash_map.get(key, {}).get(member, None)

    def remove_member(self, key: str, *members: str) -> int:
        count = 0
        if key in self.__hash_map:
            data = self.__hash_map[key]
            for member in members:
                if member in data:
                    del data[member]
                    count += 1
        return count

    def remove(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self.__overdue:
                del self.__overdue[key]

            if key in self.__hash_map:
                del self.__hash_map[key]
                count += 1
            elif key in self.__strings:
                del self.__strings[key]
                count += 1
        return count


class MockCacheProvider(Provider[Cache]):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Cache]:
        return Cache

    def factory(self, con: Container) -> Optional[Cache]:
        return MockCache()
