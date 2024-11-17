from typing import Iterable, Optional, Callable, Tuple, List

from typing_extensions import Protocol
from collections import deque
from abc import abstractmethod
from ghostos.core.messages.message import Message, MessageType
from ghostos.core.messages.pipeline import SequencePipe
import time

__all__ = ["Stream", "Receiver", "ArrayReceiver", "ArrayStream", "new_arr_connection"]


class Stream(Protocol):
    """
    an interface that can send messages asynchronously.
    """

    @abstractmethod
    def send(self, messages: Iterable[Message]) -> bool:
        """
        send batch of messages
        :return: successful. if False, maybe error occur
        """
        pass

    def deliver(self, message: Message) -> bool:
        if not message.is_complete():
            message = message.as_tail()
        return self.send([message])

    @abstractmethod
    def completes_only(self) -> bool:
        """
        if the stream receive complete message only
        :return:
        """
        pass

    @abstractmethod
    def alive(self) -> bool:
        """
        :return: the upstream channel is alive
        """
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def fail(self, error: str) -> bool:
        """
        端的 fail 会传递给 receiver.
        :param error:
        :return:
        """
        pass

    @abstractmethod
    def error(self) -> Optional[Message]:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        if not self.alive():
            return None
        intercept = None
        if exc_val is not None:
            intercept = self.fail(error=str(exc_val))
        self.close()
        return intercept


class Receiver(Protocol):
    @abstractmethod
    def recv(self) -> Iterable[Message]:
        pass

    @abstractmethod
    def cancel(self):
        pass

    @abstractmethod
    def fail(self, error: str) -> bool:
        """
        receiver 的 fail 会传递到端.
        :param error:
        :return:
        """
        pass

    @abstractmethod
    def done(self) -> bool:
        pass

    @abstractmethod
    def error(self) -> Optional[Message]:
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def wait(self) -> List[Message]:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        if self.done():
            return None
        intercept = None
        if exc_val is not None:
            intercept = self.fail(str(exc_val))
        self.close()
        return intercept


class ArrayReceiver(Receiver):

    def __init__(self, alive: Callable[[], bool], idle: float = 0.1, complete_only: bool = False):
        self._check_alive = alive
        self._idle = idle
        self._chunks = deque()
        self._completes = []
        self._closed = False
        self._done = False
        self._error: Optional[Message] = None
        self._complete_only = complete_only

    def recv(self) -> Iterable[Message]:
        if self._closed:
            raise RuntimeError("Receiver is closed")
        alive = self._check_alive
        while not self._done:
            if len(self._chunks) > 0:
                item = self._chunks.popleft()
                yield item
                continue
            is_alive = alive()
            if not is_alive:
                self._error = MessageType.ERROR.new(content="Receiver is closed")
                self._done = True
                break
            if self._idle:
                time.sleep(self._idle)
        if len(self._chunks) > 0:
            yield from self._chunks
            self._chunks = []
        if self._error is not None:
            yield self._error

    def add(self, message: Message) -> bool:
        if self._closed or self._done:
            return False
        if not self._check_alive():
            return False
        if MessageType.is_protocol_message(message):
            self._done = True
            if MessageType.ERROR.match(message):
                self._error = message
            return True
        else:
            if message.is_complete() or not self._complete_only:
                self._chunks.append(message)
            if message.is_complete():
                self._completes.append(message.get_copy())
            return True

    def cancel(self):
        self._done = True

    def fail(self, error: str) -> bool:
        self._done = True
        self._error = MessageType.ERROR.new(content=error)
        return False

    def done(self) -> bool:
        return self._done

    def error(self) -> Optional[Message]:
        return self._error

    def wait(self) -> List[Message]:
        while not self._done and not self._closed and not self._error:
            time.sleep(self._idle)
        completes = self._completes.copy()
        if self._error is not None:
            completes.append(self._error)
        return completes

    def close(self):
        if self._closed:
            return
        self._done = True
        self._error = None
        self._chunks = []
        self._completes = []
        del self._check_alive


class ArrayStream(Stream):

    def __init__(self, receiver: ArrayReceiver, complete_only: bool):
        self._receiver = receiver
        self._alive = not receiver.done()
        self._closed = False
        self._error: Optional[Message] = None
        self._complete_only = complete_only

    def send(self, messages: Iterable[Message]) -> bool:
        if self._closed or not self._alive:
            raise RuntimeError("Stream is closed")
        if self._error is not None:
            raise RuntimeError(self._error.get_content())
        items = SequencePipe().across(messages)
        for item in items:
            if self._complete_only and not item.is_complete():
                continue
            success = self._receiver.add(item)
            if success:
                continue
            self._alive = False
            self._error = self._receiver.error()
            if self._error is not None:
                raise RuntimeError(f"upstream is closed: {self._error.get_content()}")
            else:
                raise RuntimeError(f"send upstream failed")
        return True

    def completes_only(self) -> bool:
        return self._complete_only

    def alive(self) -> bool:
        if not self._alive:
            return False
        if self._receiver.done():
            self._alive = False
        return self._alive

    def close(self):
        if self._closed:
            return
        if self._alive:
            self._receiver.add(MessageType.final())
        self._alive = False
        self._closed = True
        del self._receiver

    def fail(self, error: str) -> bool:
        if self._error is not None:
            return False
        self._error = MessageType.ERROR.new(content=error)
        if self._alive:
            self._receiver.add(self._error)
        self._alive = False
        return False

    def error(self) -> Optional[Message]:
        return self._error


def new_arr_connection(
        *,
        timeout: float = -1,
        idle: float = 0.2,
        complete_only: bool = False,
) -> Tuple[Stream, Receiver]:
    """
    use array to pass and receive messages in multi-thread
    :param timeout: if negative, wait until done
    :param idle: sleep time in seconds wait for next pull
    :param complete_only: only receive complete message
    :return: created stream and receiver
    """
    from ghostos.helpers import Timeleft
    timeleft = Timeleft(timeout)

    def alive_check() -> bool:
        if not timeleft.alive():
            return False
        return True

    receiver = ArrayReceiver(alive_check, idle, complete_only)
    stream = ArrayStream(receiver, complete_only)
    return stream, receiver
