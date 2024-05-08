from abc import ABC, abstractmethod
from typing import Any


class Context(ABC):
    """
    考虑像 golang 一样提供一个 context 方便一些全局参数的传递.
    理论上要实现 with statement.
    是否要实现 context.done 则需要调研一下, 最好看看 python 有没有好的 context 项目.
    """

    @abstractmethod
    def get(self, key: str) -> Any:
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        pass

    def __enter__(self):
        # todo: enter
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        # todo: cancel parent
        pass
