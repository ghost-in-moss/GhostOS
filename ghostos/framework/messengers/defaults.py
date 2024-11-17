from typing import Optional, Iterable, List, Tuple
from ghostos.core.runtime.messenger import Messenger
from ghostos.core.messages import (
    Message, Payload, Role,
    Stream, Caller,
)
from ghostos.core.messages.pipeline import SequencePipe

__all__ = [
    'DefaultMessenger'
]


class DefaultMessenger(Messenger):

    def __init__(
            self,
            upstream: Optional[Stream],
            *,
            name: Optional[str] = None,
            role: Optional[str] = None,
            payloads: Optional[Iterable[Payload]] = None,
            stage: str = "",
    ):
        self._upstream = upstream
        self._assistant_name = name
        self._role = role if role else Role.ASSISTANT.value
        self._payloads = payloads
        self._sent_messages = []
        self._sent_callers = []
        self._stage = stage

    def flush(self) -> Tuple[List[Message], List[Caller]]:
        messages = self._sent_messages
        callers = self._sent_callers
        del self._upstream
        del self._sent_messages
        del self._sent_callers
        return messages, callers

    def send(self, messages: Iterable[Message]) -> bool:
        messages = self.buffer(messages)
        if self._upstream is not None:
            return self._upstream.send(messages)
        list(messages)
        return True

    def buffer(self, messages: Iterable[Message]) -> Iterable[Message]:
        messages = SequencePipe().across(messages)
        for item in messages:
            if item.is_complete() or item.is_head():
                item.name = self._assistant_name
                item.stage = self._stage
                if not item.role:
                    item.role = self._role

            if item.is_complete():
                if self._payloads:
                    for payload in self._payloads:
                        payload.set(item)

                self._sent_messages.append(item)
                if len(item.callers) > 0:
                    self._sent_callers.extend(item.callers)

            # skip chunk
            if self._upstream and self._upstream.completes_only() and not item.is_complete():
                continue
            yield item

    def completes_only(self) -> bool:
        return self._upstream is not None and self._upstream.completes_only()

    def alive(self) -> bool:
        return self._upstream is None or self._upstream.alive()

    def close(self):
        return

    def fail(self, error: str) -> bool:
        if self._upstream is not None:
            return self._upstream.fail(error)
        return False

    def error(self) -> Optional[Message]:
        if self._upstream is not None:
            return self._upstream.error()
        return None

    def closed(self) -> bool:
        return self._upstream is None or self._upstream.closed()



