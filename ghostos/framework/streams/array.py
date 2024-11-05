from typing import Tuple, Optional, Dict, List, Iterable, Callable
from ghostos.core.messages import (
    Message, Stream, Receiver, Received,
    MessageType,
)
import time

__all__ = ['new_connection']

from ghostos.helpers import Timeleft


def new_connection(timeout: float, accept_chunks: bool, idle: float = 0.2) -> Tuple[Stream, Receiver]:
    """
    create a stream and a receiver, which are run at different threads.
    when receiver is stopped, stream stop immediately.
    :param timeout:
    :param accept_chunks:
    :param idle:
    :return:
    """
    receiver = _ArrayReceiver(idle=idle)
    stream = _ArrayStream(receiver, timeout=timeout, accept_chunks=accept_chunks)
    return stream, receiver


class _ArrayReceiver(Receiver):
    def __init__(self, idle: float):
        self._idle = idle
        self._stopped = False
        self._received: Dict[str, _ArrayReceived] = {}
        self._msg_ids: List[str] = []
        self._final: Optional[Message] = None
        self._buffering: Optional[Message] = None
        self._destroyed: bool = False
        self._iterating: bool = False

    def add_item(self, item: Message) -> bool:
        if self._stopped:
            return False
        if MessageType.is_protocol_message(item):
            self.stop(item)
            return True

        if self._buffering is None:
            self._new_received(item)
            return True

        patched = self._buffering.patch(item)
        if patched:
            self._append_item(item)
            return True
        else:
            tail = self._buffering.as_tail()
            self._append_item(tail)
            self._new_received(item)
            return True

    def _new_received(self, item: Message) -> None:
        msg_id = item.msg_id
        if not item.is_complete():
            self._buffering = item.as_head()
            msg_id = self._buffering.msg_id
        received = _ArrayReceived(item, idle=self.idle)
        self._received[msg_id] = received
        self._msg_ids.append(msg_id)

    def _append_item(self, item: Message) -> None:
        msg_id = self._buffering.msg_id
        received = self._received[msg_id]
        received.add_item(item)

    def stopped(self) -> bool:
        return self._stopped

    def idle(self) -> bool:
        time.sleep(self._idle)
        return not self._stopped

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._stopped:
            return
        self.destroy()

    def __enter__(self) -> Iterable[Received]:
        if self._iterating:
            raise RuntimeError("Cannot iterating Retriever at the same time")
        self._iterating = True
        idx = 0
        while not self._stopped:
            if idx < len(self._msg_ids):
                msg_id = self._msg_ids[idx]
                idx += 1
                yield self._received[msg_id]
            else:
                time.sleep(self._idle)
        while idx < len(self._msg_ids):
            yield self._received[self._msg_ids[idx]]
            idx += 1
        if self._final and MessageType.ERROR.match(self._final):
            yield _ArrayReceived(self._final, idle=self.idle)
        self._iterating = False

    def stop(self, item: Optional[Message]) -> None:
        if self._stopped:
            return
        self._stopped = True
        if self._buffering:
            tail = self._buffering.as_tail()
            self._append_item(tail)
        self._buffering = None
        self._final = item

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        self._stopped = True
        for item in self._received.values():
            item.destroy()
        del self._buffering
        del self._final
        del self._msg_ids
        del self._received


class _ArrayStream(Stream):

    def __init__(self, receiver: _ArrayReceiver, timeout: float, accept_chunks: bool = True):
        self._receiver = receiver
        self._stopped = receiver.stopped()
        self._accept_chunks = accept_chunks
        self._timeleft = Timeleft(timeout)

    def deliver(self, pack: "Message") -> bool:
        if self._stopped:
            return False
        if not self._timeleft.alive():
            e = TimeoutError(f"Timeout after {self._timeleft.passed()}")
            self._receiver.stop(MessageType.ERROR.new(content=str(e)))
            raise e
        if pack.chunk and not self._accept_chunks:
            return True
        success = self._receiver.add_item(pack)
        if success:
            return True
        if self._receiver.stopped():
            self.stop()
        return False

    def __exit__(self, exc_type, exc_val, exc_tb):
        item = None
        if exc_val:
            item = MessageType.ERROR.new(content=str(exc_val))
        if not self._stopped:
            self._receiver.stop(item)
        self.stop()

    def accept_chunks(self) -> bool:
        return self._accept_chunks

    def stopped(self) -> bool:
        if self._stopped:
            return self._stopped
        self._stopped = self._receiver.stopped()
        return self._stopped

    def stop(self):
        if self._stopped:
            return
        self._stopped = True
        del self._receiver


class _ArrayReceived(Received):

    def __init__(self, head: Message, idle: Callable) -> None:
        self._idle = idle
        self._items: List[Dict] = [head.model_dump(exclude_defaults=True)]
        self._stopped = False
        self._tail: Optional[Message] = None
        if head.is_complete() or MessageType.is_protocol_message(head):
            self._tail = head.as_tail()
        self._destroyed = False

    def add_item(self, item: Message) -> None:
        if item.is_complete() or MessageType.is_protocol_message(item):
            self._tail = item.as_tail()
        else:
            self._items.append(item.model_dump(exclude_defaults=True))

    def head(self) -> Message:
        return Message(**self._items[0])

    def chunks(self) -> Iterable[Message]:
        if self._tail:
            for item in self._items:
                yield Message(**item)
            return
        idx = 0
        while self._tail is None and not self._stopped:
            if idx < len(self._items):
                yield Message(**self._items[idx])
                idx += 1
            else:
                self._stopped = self._idle()
        while idx < len(self._items):
            yield Message(**self._items[idx])
            idx += 1

    def destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        self._stopped = True
        del self._items
        del self._tail
        del self._idle

    def done(self) -> Message:
        if self._tail:
            return self._tail
        failed = 0
        while not self._stopped:
            if failed > 3:
                break
            if self._tail:
                return self._tail
            if not self._idle():
                failed += 1
        if self._tail:
            return self._tail
        raise RuntimeError(f"empty tail message")
