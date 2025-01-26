from typing import Iterable
from ghostos.core.messages import Message
from ghostos.core.messages.pipeline import SequencePipe, run_pipeline


def test_multi_sequence_pipes():
    content = "hello world"

    def iter_content(c: str) -> Iterable[Message]:
        for char in c:
            yield Message.new_chunk(content=char)

    messages = iter_content(content)
    parsed = run_pipeline([SequencePipe(), SequencePipe(), SequencePipe()], messages)
    got = list(parsed)
    assert len(got) == len(content) + 1
    assert got[0].is_head()
    assert got[0].created > 0
    assert got[0].content == "h"
    assert got[-1].is_complete()
    assert got[-2].is_chunk()


def test_multi_sequence_pipe_with_tail():
    content = "hello world"

    def iter_content(c: str) -> Iterable[Message]:
        for char in c:
            yield Message.new_chunk(content=char)

    messages = iter_content(content)
    messages = SequencePipe().across(messages)
    messages = list(messages)
    assert len(messages) == len(content) + 1
    messages = SequencePipe().across(messages)
    messages = list(messages)
    assert len(messages) == len(content) + 1


def test_sequence_pipe_with_tail():
    item = Message.new_tail(content="hello")
    messages = SequencePipe().across([item])
    messages = list(messages)
    assert len(messages) == 1


def test_sequence_pipe_with_2_tails():
    item1 = Message.new_tail(content="hello")
    item2 = Message.new_tail(content="world")
    messages = SequencePipe().across([item1, item2])
    messages = list(messages)
    assert len(messages) == 2
