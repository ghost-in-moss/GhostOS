from abc import ABC, abstractmethod
from typing import Iterable
from ghostiss.core.messages.message import Message

__all__ = [
    "Stream",
]


class Stream(ABC):
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
    def send(self, messages: Iterable[Message]) -> bool:
        """
        发送消息.
        """
        pass

    @abstractmethod
    def stopped(self) -> bool:
        """
        是否已经停止接受
        """
        pass
