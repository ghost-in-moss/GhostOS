from abc import ABC, abstractmethod
from typing import Iterable, Tuple, Optional, Callable
from ghostos.core.messages.message import Message

__all__ = [
    "Stream",
    "Receiver", "Received",
]


class Stream(ABC):
    """
    streaming output messages.
    with stream:
        stream.send(message_item)
        ...
        # when the stream exits, it will send the protocol final item.

    1. when stream context is exited, the stream send final message to the receiver.
    2. when a protocol item send to stream, it will stop.
    """

    @abstractmethod
    def deliver(self, pack: "Message") -> bool:
        """
        deliver a message.
        a message shall be a head, chunk or a tail.
        - head: first chunk message with msg id
        - chunk: part of the complete message, if msg id exists, should be the same as head.
        - tail: complete message that join all the chunks, has msg_id

        when msg type is Protocol type, means the stream shall stop.

        stream can deliver multiple batch of message chunks. like:
        [tail], [head, chunk, chunk, tail], [head, tail], [tail, tail, tail]
        - tail only: one complete message at a time.
        - head => chunks => tail: normal sequences of chunks.
        - head => tail: no chunks needed
        - tail => tail: the new tail shall replace the current tail.

        if an error message or a final message is delivering, the stream usually stop immediately.
        :return: if the message was delivered. if the stream is stopped, return False.
        """
        pass

    @abstractmethod
    def accept_chunks(self) -> bool:
        """
        weather the stream is sending chunks.
        if False, the stream will ignore all the chunks
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

    def __enter__(self):
        return self

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class Received(ABC):
    """
    api for a batch of message chunks
    """

    @abstractmethod
    def head(self) -> Message:
        """
        :return: head chunk of the message chunks.
        may be the head chunk is the tail.
        """
        pass

    @abstractmethod
    def chunks(self) -> Iterable[Message]:
        """
        iterate over the message chunks.
        from head (if head is not the tail) to the last chunk
        """
        pass

    @abstractmethod
    def done(self) -> Message:
        """
        retail the complete message of the chunks.
        """
        pass


class Receiver(ABC):
    @abstractmethod
    def __enter__(self) -> Iterable[Received]:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


new_connection = Callable[[], Tuple[Stream, Receiver]]
