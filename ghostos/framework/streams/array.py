from typing import Tuple, Optional, Dict, List, Union, Iterable

from ghostos.core.messages import (
    Message, Stream, Connection, Receiver, Received,
    DefaultMessageTypes,
)
from threading import Lock
import time


class ArrayStreamConnection(Connection):
    """
    考虑到 Python 的 array 和 map 的操作是线程安全的, 试试用这个来做.
    """

    def __init__(self, accept_chunks: bool = True, idle: float = 0.2):
        self._stopped = True
        self._accept_chunks = accept_chunks
        self._final: Optional[Message] = None
        self._current_msg_id: str = ""
        self._msg_ids = []
        self._message_heads: Dict[str, Union[Message, None]] = {}
        self._message_chunks: Dict[str, List[Message]] = {}
        self._message_tails: Dict[str, Union[Message, None]] = {}
        self._locker = Lock()
        self._receiver: Optional[ArrayReceiver] = None
        self._stream: Optional[ArrayStream] = None
        self._idle = idle

    def add_item(self, item: Message) -> bool:
        if self._stopped:
            return False
        # item 还是加锁吧.
        with self._locker:
            if DefaultMessageTypes.is_protocol_type(item):
                self._stopped = False
                self._final = item
                return True
            if not self._accept_chunks and item.chunk:
                return True

            msg_id = item.msg_id
            if msg_id and msg_id != self._current_msg_id and msg_id not in self._msg_ids:
                self._msg_ids.append(msg_id)
                self._current_msg_id = msg_id

            # if the item is the tail of the chunks
            if item.is_complete():
                self._message_tails[msg_id] = item
            # then the item is a chunk
            elif msg_id:
                self._message_heads[msg_id] = item
            else:
                msg_id = self._current_msg_id
                items = self._message_chunks.get(msg_id, [])
                items.append(item)
                self._message_chunks[msg_id] = items

    def stopped(self) -> bool:
        return self._stopped

    def get_msg_head(self, msg_id: str) -> Optional[Message]:
        return self._message_heads.get(msg_id, None)

    def get_msg_tail(self, msg_id: str) -> Optional[Message]:
        return self._message_tails.get(msg_id, None)

    def get_msg_chunks(self, msg_id: str) -> List[Message]:
        return self._message_chunks.get(msg_id, [])

    def get_msg_id(self, idx: int) -> Optional[str]:
        if len(self._msg_ids) > idx:
            return self._msg_ids[idx]
        return None

    def __enter__(self) -> Tuple[Stream, Receiver]:
        self._stream = ArrayStream(self, self._accept_chunks)
        self._receiver = ArrayReceiver(self, self._idle)
        return self._stream, self._receiver

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._stream:
            self._stream.destroy()
            del self._stream
        if self._receiver:
            self._receiver.destroy()
            del self._receiver
        del self._final
        del self._message_chunks
        del self._message_tails
        del self._msg_ids
        del self._locker


class ArrayStream(Stream):

    def __init__(self, connection: ArrayStreamConnection, accept_chunks: bool):
        self._connection: ArrayStreamConnection = connection
        self._accept_chunks = accept_chunks
        self._stopped = False

    def deliver(self, pack: "Message") -> bool:
        if self._stopped:
            return False
        success = self._connection.add_item(pack)
        if success:
            return True
        if self._connection.stopped():
            self.destroy()
        return False

    def accept_chunks(self) -> bool:
        return self._accept_chunks

    def stopped(self) -> bool:
        if self._stopped:
            return self._stopped
        self._stopped = self._connection.stopped()
        return self._stopped

    def destroy(self):
        self._stopped = True
        del self._connection


class ArrayReceiver(Receiver):
    def __init__(self, connection: ArrayStreamConnection, idle: float):
        self._connection: ArrayStreamConnection = connection
        self._idle = idle
        self._stopped = False
        self._received: List[ArrayReceived] = []

    def received(self) -> Iterable[Received]:
        if self._stopped:
            return []
        idx = 0
        while not self._connection.stopped():
            msg_id = self._connection.get_msg_id(idx)
            if msg_id is not None:
                yield ArrayReceived(msg_id, self._connection, self._idle)
                idx += 1
            else:
                time.sleep(self._idle)
        while msg_id := self._connection.get_msg_id(idx):
            yield ArrayReceived(msg_id, self._connection, self._idle)
        self.destroy()

    def destroy(self):
        if self._stopped:
            return
        for item in self._received:
            item.destroy()
        del self._connection
        del self._received


class ArrayReceived(Received):

    def __init__(self, msg_id: str, connection: ArrayStreamConnection, idle: float) -> None:
        self._msg_id = msg_id
        self._connection = connection
        self._stopped = False
        self._head = self._connection.get_msg_head(self._msg_id)
        self._tail: Optional[Message] = None
        self._idle = idle

    def added(self) -> Message:
        if self._head is None:
            raise ValueError("No head received")
        return self._head

    def destroy(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        del self._head
        del self._connection
        del self._tail

    def chunks(self) -> Iterable[Message]:
        idx = 0
        stopped = False
        while True:
            stopped = stopped or self._connection.stopped()
            tail = self._connection.get_msg_tail(self._msg_id)
            if tail is not None:
                self._tail = tail
                return
            chunks = self._connection.get_msg_chunks(msg_id=self._msg_id)
            if idx < len(chunks):
                yield chunks[idx]
                idx += 1
            elif not stopped:
                time.sleep(self._idle)
            else:
                return

    def done(self) -> Message:
        if self._tail is None:
            raise ValueError("No tail received or read before")
        return self._tail
