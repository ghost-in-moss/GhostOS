from __future__ import annotations
from typing import Iterable, Optional, Tuple, List, Iterator
from typing_extensions import Protocol, Self
from collections import deque
from abc import abstractmethod
from ghostos.core.messages.message import Message, MessageType
from ghostos.core.messages.pipeline import SequencePipe
from ghostos.errors import StreamingError
import time

__all__ = [
    "Stream", "Receiver", "ArrayReceiver", "ArrayStream", "new_basic_connection", 'ListReceiver',
    "ReceiverBuffer",
]

from ghostos_common.helpers import Timeleft


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

    def allow_streaming(self) -> bool:
        return not self.completes_only()

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

    @abstractmethod
    def closed(self) -> bool:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        if self.closed():
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
    def closed(self) -> bool:
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
        if self.closed():
            return None
        intercept = None
        if exc_val is not None:
            intercept = self.fail(str(exc_val))
        self.close()
        return intercept


class ListReceiver(Receiver):
    """
    fake receiver with defined list items
    """

    def __init__(self, items: List[Message]):
        self._items = items
        self._closed = False

    def recv(self) -> Iterable[Message]:
        yield from self._items
        self._closed = True

    def cancel(self):
        return

    def fail(self, error: str) -> bool:
        return False

    def closed(self) -> bool:
        return self._closed

    def error(self) -> Optional[Message]:
        return None

    def close(self):
        self._closed = True

    def wait(self) -> List[Message]:
        items = self._items
        self.close()
        return items


class ArrayReceiver(Receiver):

    def __init__(
            self,
            timeleft: Timeleft,
            idle: float = 0.1,
            complete_only: bool = False,
            request_timeout: float = 0.0,
    ):
        self._timeleft = timeleft
        self._idle = idle
        self._streaming = deque()
        self._closed = False
        self._done = False
        self._error: Optional[Message] = None
        self._complete_only = complete_only
        self._request_timeout = request_timeout

    def recv(self) -> Iterable[Message]:
        if self._closed:
            raise RuntimeError("Receiver is closed")
        received_any = False
        first_token_timeleft = Timeleft(self._request_timeout if not self._complete_only else 0.0)
        while not self._done:
            if len(self._streaming) > 0:
                received_any = True
                item = self._streaming.popleft()
                yield item
                continue
            if not self._timeleft.alive():
                self._error = MessageType.ERROR.new(content=f"Timeout after {self._timeleft.passed()}")
                self._done = True
                break
            if self._idle:
                if not received_any and not first_token_timeleft.alive():
                    self._error = MessageType.ERROR.new(content=f"First token timeout after {self._timeleft.passed()}")
                    break
                time.sleep(self._idle)
        if len(self._streaming) > 0:
            yield from self._streaming
            self._streaming.clear()
        if self._error is not None:
            yield self._error

    def add(self, message: Message) -> bool:
        if self._closed:
            return False
        if MessageType.is_protocol_message(message):
            self._done = True
            if MessageType.ERROR.match(message):
                self._error = message
            return True

        elif self._done or not self._timeleft.alive():
            return False
        else:
            if message.is_complete() or not self._complete_only:
                self._streaming.append(message)
            return True

    def cancel(self):
        self._done = True

    def fail(self, error: str) -> bool:
        if self._error is not None:
            return False
        self._done = True
        self._error = MessageType.ERROR.new(content=error)
        return False

    def closed(self) -> bool:
        return self._closed

    def error(self) -> Optional[Message]:
        return self._error

    def wait(self) -> List[Message]:
        items = list(self.recv())
        completes = []
        for item in items:
            if item.is_complete():
                completes.append(item)
        return completes

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._done = True
        self._streaming.clear()
        self._timeleft = None


class ArrayStream(Stream):

    def __init__(self, receiver: ArrayReceiver, complete_only: bool):
        self._receiver = receiver
        self._alive = not receiver.closed()
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
                raise StreamingError(
                    f"streaming is failed: {self._error.get_content()}, message {item.model_dump_json()} unsent"
                )
            elif self._receiver.closed():
                raise StreamingError(
                    f"streaming is failed due to receiver is closed: , message {item.model_dump_json()} unsent"
                )
            elif not self.alive():
                raise StreamingError(
                    f"streaming is closed, message {item.model_dump_json()} unsent",
                )
            else:
                raise StreamingError(f"send stream failed, message {item.model_dump_json()} unsent")
        return True

    def completes_only(self) -> bool:
        return self._complete_only

    def alive(self) -> bool:
        if not self._alive:
            return False
        if self._receiver.closed():
            self._alive = False
        return self._alive

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._error:
            self._receiver.add(self._error)
        else:
            self._receiver.add(MessageType.final())
        self._alive = False
        del self._receiver

    def fail(self, error: str) -> bool:
        if self._error is not None:
            return False
        self._error = MessageType.ERROR.new(content=error)
        self._alive = False
        return False

    def error(self) -> Optional[Message]:
        return self._error

    def closed(self) -> bool:
        return self._closed


class ReceiverBuffer:
    def __init__(self, head: Message, iterator: Iterator[Message]):
        if head.is_chunk():
            head = head.as_head()
        self._head = head
        self._iterator = iterator
        self._chunks = []
        self._done: Optional[Message] = None
        self._next: Optional[Self] = None

    @classmethod
    def new(cls, receiving: Iterable[Message]) -> Optional[Self]:
        try:
            iterator = iter(receiving)
            head = next(iterator)
        except StopIteration:
            return None
        if head is None:
            return None
        return cls(head, iterator)

    def head(self) -> Message:
        return self._head

    def chunks(self) -> Iterable[Message]:
        if self._head.is_complete():
            yield from [self._head]
            return
        elif self._done is not None:
            return self._chunks

        self._chunks = [self._head]
        yield self._head
        head = self._head.get_copy()
        try:
            item = next(self._iterator)
        except StopIteration:
            self._done = head.as_tail()
            return None

        while item is not None:
            patched = head.patch(item)
            if patched is not None:
                head = patched
                if item.is_complete():
                    self._done = patched
                else:
                    self._chunks.append(item)
                    yield item
            else:
                if self._done is None:
                    self._done = head.as_tail()
                self._next = ReceiverBuffer(item, self._iterator)
                self._iterator = None
                break
            try:
                item = next(self._iterator)
            except StopIteration:
                break
        if self._done is None:
            self._done = self._head.as_tail()

    def tail(self) -> Message:
        if self._head.is_complete():
            return self._head
        if self._done:
            return self._done
        list(self.chunks())
        if self._done is None:
            self._done = self._head.as_tail()
        return self._done

    def next(self) -> Optional[Self]:
        self.tail()
        if self._next is not None:
            return self._next
        else:
            try:
                item = next(self._iterator)
                iterator = self._iterator
                self._iterator = None
                return ReceiverBuffer(item, iterator)
            except StopIteration:
                return None


def new_basic_connection(
        *,
        timeout: float = 0.0,
        idle: float = 0.2,
        complete_only: bool = False,
        request_timeout: float = 0.0,
) -> Tuple[Stream, Receiver]:
    """
    use array to pass and receive messages in multi-thread
    :param timeout: if negative, wait until done
    :param idle: sleep time in seconds wait for next pull
    :param complete_only: only receive complete message
    :param request_timeout: first token timeout. only work when complete_only is False
    :return: created stream and receiver
    """
    from ghostos_common.helpers import Timeleft
    timeleft = Timeleft(timeout)
    receiver = ArrayReceiver(timeleft, idle, complete_only, request_timeout)
    stream = ArrayStream(receiver, complete_only)
    return stream, receiver
