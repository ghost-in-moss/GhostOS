from abc import ABC, abstractmethod
from typing import Iterable, Tuple
from ghostos.core.messages.message import Message

__all__ = [
    "Stream",
    "Receiver", "Received",
    "Connection",
]


class Stream(ABC):
    """
    streaming output messages.
    """

    @abstractmethod
    def deliver(self, pack: "Message") -> bool:
        """
        deliver a pack of message, may be a chunk
        if an error message or a final message is delivering, the stream usually stop immediately.
        but nesting stream can accept multiple final messages, only stop when it's done method is called.
        :return: if the message was delivered. if the stream is stopped, return False.
        """
        pass

    @abstractmethod
    def accept_chunks(self) -> bool:
        """
        weather the stream is sending chunks.
        if False, the stream will send joined chunks as a single message only.
        """
        pass

    def send(self, messages: Iterable[Message]) -> bool:
        """
        syntax sugar for delivering
        """
        for item in messages:
            ok = self.deliver(item)
            if not ok:
                # break sending
                return False
        return True

    @abstractmethod
    def stopped(self) -> bool:
        """
        if the stream is stopped.
        """
        pass


class Received(ABC):

    @abstractmethod
    def added(self) -> Message:
        pass

    @abstractmethod
    def chunks(self) -> Iterable[Message]:
        pass

    @abstractmethod
    def done(self) -> Message:
        pass


class Receiver(ABC):
    @abstractmethod
    def received(self) -> Iterable[Received]:
        pass


class Connection(ABC):
    @abstractmethod
    def __enter__(self) -> Tuple[Stream, Receiver]:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        pass
