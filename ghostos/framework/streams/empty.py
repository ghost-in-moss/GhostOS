from typing import Iterable

from ghostos.core.messages import Stream, Message, DefaultMessageTypes


class EmptyStream(Stream):

    def __init__(self, max_final: int = 0):
        self._max_final = max_final
        self._final_count = 0

    def deliver(self, pack: "Message") -> bool:
        if self.stopped():
            return False
        if DefaultMessageTypes.is_final(pack):
            self._final_count += 1
        return True

    def is_streaming(self) -> bool:
        return False

    def send(self, messages: Iterable[Message]) -> bool:
        for item in messages:
            if not self.deliver(item):
                return False
        return True

    def stopped(self) -> bool:
        return self._final_count > self._max_final
