from typing import Iterable

from ghostos.core.messages import Stream, Message, DefaultMessageTypes


class EmptyStream(Stream):
    """
    for mock or test
    """

    def __init__(self, max_final: int = 0):
        self._max_final = max_final
        self._final_count = 0

    def deliver(self, pack: "Message") -> bool:
        if self.stopped():
            return False
        if DefaultMessageTypes.is_final(pack):
            self._final_count += 1
        return True

    def accept_chunks(self) -> bool:
        return False

    def stopped(self) -> bool:
        return self._final_count > self._max_final
