from typing import Iterable, Optional
from typing_extensions import Self
from abc import ABC, abstractmethod
from ghostos.core.messages.message import Message, MessageType

__all__ = [
    'Pipe', 'run_pipeline', "SequencePipe", 'TailPatchPipe',
]


class Pipe(ABC):

    @abstractmethod
    def new(self) -> Self:
        pass

    @abstractmethod
    def across(self, messages: Iterable[Message]) -> Iterable[Message]:
        pass


def run_pipeline(pipes: Iterable[Pipe], messages: Iterable[Message]) -> Iterable[Message]:
    """
    build pipeline with pipes
    :param pipes:  from input to output
    :param messages:
    :return:
    """
    ordered = list(pipes)
    outputs = messages
    for pipe in ordered:
        outputs = pipe.across(messages)
        messages = outputs
    yield from outputs


class SequencePipe(Pipe):
    """
    make sure messages are sent in a ?head-?chunk-tail-?tail sequence
    """

    def new(self) -> Self:
        return SequencePipe()

    def across(self, messages: Iterable[Message]) -> Iterable[Message]:
        buffer: Optional[Message] = None
        final: Optional[Message] = None
        for item in messages:
            if MessageType.is_protocol_message(item):
                final = item
                break
            if buffer is None:
                if item.is_complete():
                    buffer = item
                    continue
                else:
                    # yield head
                    buffer = item.as_head()
                    yield buffer.get_copy()
                    continue
            else:
                patched = buffer.patch(item)
                if patched:
                    if patched.is_complete():
                        buffer = patched
                        continue
                    else:
                        # add msg_id to item, keep every chunk has it id
                        if not item.msg_id:
                            item.msg_id = buffer.msg_id
                        yield item
                else:
                    yield buffer.as_tail()
                    buffer = item.get_copy()
                    if buffer.is_chunk():
                        buffer = buffer.as_head(copy=False)
                    if not buffer.is_complete():
                        yield buffer.get_copy()
                    continue
        if buffer is not None:
            yield buffer.as_tail(copy=False)
        if final is not None:
            yield final


class CompleteOnly(Pipe):
    """
    return complete only
    """

    def new(self) -> Self:
        return CompleteOnly()

    def across(self, messages: Iterable[Message]) -> Iterable[Message]:
        for item in messages:
            if MessageType.is_protocol_message(item):
                yield item
                break
            elif item.is_complete():
                yield item


class TailPatchPipe(Pipe):

    def new(self) -> Self:
        return TailPatchPipe()

    def across(self, messages: Iterable[Message]) -> Iterable[Message]:
        last_tail: Optional[Message] = None
        for item in messages:
            if MessageType.is_protocol_message(item):
                yield item
                break
            if not item.is_complete():
                yield item
                continue
            if last_tail is None:
                last_tail = item
                continue
            patched = last_tail.patch(item)
            if patched:
                last_tail = patched
                continue
            yield last_tail.as_tail()
            last_tail = item
