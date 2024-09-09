from typing import Iterable

from ghostos.core.messages import Stream, Message, DefaultMessageTypes
from queue import Queue

__all__ = ["QueueStream"]


class QueueStream(Stream):

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
        elif self._streaming and not pack.is_tail():
            # 不发送间包, 只发送尾包.
            return True
        else:
            self._queue.put(pack, block=True)
            return True

    def is_streaming(self) -> bool:
        return self._streaming

    def send(self, messages: Iterable[Message]) -> bool:
        for item in messages:
            ok = self.deliver(item)
            if not ok:
                return False
        return True

    def stopped(self) -> bool:
        return self._stopped
