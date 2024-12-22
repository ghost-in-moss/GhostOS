from typing import Iterable, List, NamedTuple
from abc import ABC, abstractmethod

from ghostos.core.messages.message import Message, FunctionCaller

__all__ = [
    "Flushed", "Buffer",
]


class Flushed(NamedTuple):
    unsent: Iterable[Message]
    """ the unsent messages or chunks, which were buffed"""

    messages: List[Message]
    """all the patched complete messages"""

    callers: List[FunctionCaller]
    """all the callers that delivered"""


class Buffer(ABC):
    """
    a container to buff streaming Message chunks,
    and patched all the chunks,
    return complete patched messages after flushed.
    在流式传输中拦截 message 的拦截器. 同时要能完成粘包, 最终返回粘包后的结果.
    """

    @abstractmethod
    def add(self, pack: "Message") -> Iterable[Message]:
        """
        try to buff a message pack
        :return: the sending messages after the buffing. may be:
        1. the input pack, which need not be buffered
        2. the unsent packs, which are replaced by new buffing pack.
        """
        pass

    @abstractmethod
    def flush(self) -> Flushed:
        """
        flush the buffered messages, and reset itself.
        """
        pass
