from typing import Optional

from ghostos.contracts.cache import Cache


class MockCache(Cache):

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


if __name__ == '__main__':
    from ghostos.prototypes.console import run_demo_thought
    from ghostos.thoughts import new_pymodule_editor_thought

    run_demo_thought(new_pymodule_editor_thought(__name__))
