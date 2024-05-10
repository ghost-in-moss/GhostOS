from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict


class Session(ABC):
    """
    Ghost 的会话构建.
    """

    @abstractmethod
    def shells(self) -> Dict[str, Shell]:
        pass


class Shell(ABC):
    """
    Ghost 所在的 Shell.
    提供 API 操作自己的 Shell.
    一个有状态的 Ghost 可以同时存在于多个 Shell.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        pass
