from typing import List, Iterable, Optional, Tuple
from typing_extensions import Self
from abc import ABC, abstractmethod
from ghostos.core.messages.message import Message


class Buffer(ABC):

    @abstractmethod
    def new(self) -> Self:
        pass

    @abstractmethod
    def match(self, message: Message) -> bool:
        pass

    @abstractmethod
    def buffer(self, message: Message) -> Iterable[Message]:
        pass

    @abstractmethod
    def flush(self) -> Tuple[List[Message], List[Message]]:
        pass


class GroupBuffer(Buffer):
    def __init__(self, default: Buffer, buffers: Iterable[Buffer]):
        self._default = default
        self._buffers = list(buffers)
        self._current: Optional[Buffer] = None
        self._completes: List[Message] = []

    def new(self) -> Self:
        return GroupBuffer(buffers=self._buffers)

    def match(self, message: Message) -> bool:
        return True

    def _find_buffer(self, message: Message) -> Buffer:
        for buffer in self._buffers:
            if buffer.match(message):
                return buffer.new()
        return self._default.new()

    def buffer(self, message: Message) -> Iterable[Message]:
        if self._current is None:
            self._current = self._find_buffer(message)
            yield from self._current.buffer(message)
        elif self._current.match(message):
            yield from self._current.buffer(message)
        else:
            unsent, completes = self._current.flush()
            self._completes.extend(completes)
            yield from unsent
            self._current = self._find_buffer(message)
            yield from self._current.buffer(message)

    def flush(self) -> Tuple[List[Message], List[Message]]:
        unsent = []
        if self._current is not None:
            unsent, completes = self._current.flush()
            self._completes.extend(completes)
        self._current = None
        completes = self._completes
        self._completes = []
        return unsent, completes
