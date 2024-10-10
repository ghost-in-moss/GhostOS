from typing import Iterable

from ghostos.core.messages import Stream, Message, DefaultMessageTypes
from queue import Queue

__all__ = ["QueueStream"]


class QueueStream(Stream):
    """
    expect to develop a thread-safe stream by python queue.
    but I'm not familiar to python thread safe queue...
    """

    def __init__(self, queue: Queue, streaming: bool = True, max_final: int = 1):
        self._queue = queue
        self._streaming = streaming
        self._stopped = False
        self._max_final = max_final
        self._final_count = 0

    def deliver(self, pack: "Message") -> bool:
        if self._stopped:
            return False
        if DefaultMessageTypes.is_protocol_type(pack):
            if DefaultMessageTypes.ERROR.match(pack):
                self._queue.put(pack, block=True)
                self._queue.task_done()
                self._stopped = True
            elif DefaultMessageTypes.FINAL.match(pack):
                self._final_count += 1
                if self._final_count >= self._max_final:
                    self._stopped = True
                    self._queue.task_done()
                    self._queue.put(pack, block=True)
            return True
        elif self._streaming and not pack.is_complete():
            # 不发送间包, 只发送尾包.
            return True
        else:
            self._queue.put(pack, block=True)
            return True

    def accept_chunks(self) -> bool:
        return not self._streaming

    def stopped(self) -> bool:
        return self._stopped

    def close(self):
        self._stopped = True
