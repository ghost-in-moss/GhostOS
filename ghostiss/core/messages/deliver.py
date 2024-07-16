from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterable, NamedTuple
if TYPE_CHECKING:
    from ghostiss.core.messages.message import Message, Caller

__all__ = [
    "Deliver",
    "Stream",
    "Decoded",
]


class Decoded(NamedTuple):
    messages: Iterable["Message"]
    """已经向上游发送的消息"""

    callers: Iterable["Caller"]
    """过滤出来的 caller. """


class Stream(ABC):
    """
    向上游发送包. 如果为 false, 则意味着不允许发送.
    """

    @abstractmethod
    def deliver(self, pack: "Message") -> bool:
        pass


class Deliver(Stream, ABC):
    """
    messenger 的原型. Stream 的有状态版本.
    """

    @abstractmethod
    def deliver(self, pack: "Message") -> bool:
        """
        发送一个包.
        """
        pass

    @abstractmethod
    def flush(self) -> None:
        """
        将所有未发送的消息都发送. 然后停止运行.
        """
        pass

    @abstractmethod
    def decoded(self) -> "Decoded":
        """
        已经缓冲的消息.
        """
        pass

    @abstractmethod
    def stopped(self) -> bool:
        """
        是否已经停止接受
        """
        pass

