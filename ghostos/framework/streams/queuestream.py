from typing import Iterable, Optional

from ghostos.core.messages import Stream, Message, DefaultMessageTypes
from queue import Queue

__all__ = ["QueueStream"]


class QueueStream(Stream):
    """
    expect to develop a thread-safe stream by python queue.
    but I'm not familiar to python thread safe queue...
    """

    def __init__(self, queue: Queue, accept_chunks: bool = True):
        self._queue = queue
        self._accept_chunks = accept_chunks
        self._stopped = False

    def deliver(self, pack: "Message") -> bool:
        if self._stopped:
            return False
        if DefaultMessageTypes.is_protocol_message(pack):
            return True
        elif self._accept_chunks and not pack.is_complete():
            # 不发送间包, 只发送尾包.
            return True
        else:
            self._queue.put(pack, block=True)
            return True

    def accept_chunks(self) -> bool:
        return not self._accept_chunks

    def stopped(self) -> bool:
        return self._stopped

    def stop(self, error: Optional[Exception]) -> None:
        if self._stopped:
            return
        self._stopped = True
        if error:
            final = DefaultMessageTypes.ERROR.new(content=str(error))
        else:
            final = DefaultMessageTypes.final()
        self._queue.put(final)
        self._queue.task_done()
        del self._queue

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop(exc_val)
