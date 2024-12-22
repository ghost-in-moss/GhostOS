from typing import Optional

from ghostos.contracts.cache import Cache


class StorageCacheImpl(Cache):

    def lock(self, key: str, overdue: int = 0) -> bool:
        pass

    def unlock(self, key: str) -> bool:
        pass

    def set(self, key: str, val: str, exp: int = 0) -> bool:
        pass

    def get(self, key: str) -> Optional[str]:
        pass

    def expire(self, key: str, exp: int) -> bool:
        pass

    def set_member(self, key: str, member: str, value: str) -> bool:
        pass

    def get_member(self, key: str, member: str) -> Optional[str]:
        pass

    def remove(self, *keys: str) -> int:
        pass