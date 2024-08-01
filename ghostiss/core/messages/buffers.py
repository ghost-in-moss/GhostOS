from typing import Iterable, List, NamedTuple
from abc import ABC, abstractmethod

from ghostiss.core.messages.message import Message, Caller

__all__ = [
    "Flushed", "Buffer",
]


class Flushed(NamedTuple):
    unsent: Iterable[Message]
    """ buffer 尚未发送, 需要继续发送出去的包"""

    messages: List[Message]
    """经过 buff, 生成的包"""

    callers: List[Caller]
    """消息体产生的回调方法."""


class Buffer(ABC):
    """
    在流式传输中拦截 message 的拦截器. 同时要能完成粘包, 返回粘包后的结果.
    """

    @abstractmethod
    def match(self, message: Message) -> bool:
        """
        匹配一个消息体.
        """
        pass

    @abstractmethod
    def buff(self, pack: "Message") -> List[Message]:
        """
        buff 一个消息体, 然后决定是否对外发送.
        不能用 Iterable 返回, 如果上层不处理, 就会导致没有 buff.
        """
        pass

    @abstractmethod
    def new(self) -> "Buffer":
        pass

    @abstractmethod
    def flush(self) -> Flushed:
        pass
