from typing import Iterable
from ghostos.core.messages.transport import new_arr_connection, Stream
from ghostos.core.messages.pipeline import SequencePipe
from ghostos.core.messages.message import Message
from threading import Thread
import time


def iter_content(content: str, gap: float) -> Iterable[Message]:
    for c in content:
        item = Message.new_chunk(content=c)
        yield item
        if gap > 0:
            time.sleep(gap)


def test_new_connection_baseline():
    stream, retriever = new_arr_connection(timeout=5, idle=0.2, complete_only=False)
    assert stream.alive()
    assert not retriever.closed()
    content = "hello world, ha ha ha ha"

    def send_data(s: Stream, c: str):
        with s:
            s.send(iter_content(c, 0.02))

    t = Thread(target=send_data, args=(stream, content))
    t.start()
    last = None
    first = None
    with retriever:
        count = 0
        for item in retriever.recv():
            if not first:
                first = item
            count += 1
            last = item
    assert count == len(content) + 1
    assert first is not None
    assert first.is_head()
    assert last.is_complete()
    t.join()


def test_new_connection_complete_only():
    stream, retriever = new_arr_connection(timeout=5, idle=0.2, complete_only=True)
    content = "hello world"

    def send_data(s: Stream, c: str):
        with s:
            s.send(iter_content(c, 0.02))

    t = Thread(target=send_data, args=(stream, content))
    t.start()
    with retriever:
        messages = list(retriever.recv())
    assert len(messages) == 1
    assert messages[0].is_complete()
    assert messages[0].content == content
    t.join()


def test_new_connection_timeout():
    stream, retriever = new_arr_connection(timeout=0.2, idle=0.2, complete_only=False)
    content = "hello world"

    def send_data(s: Stream, c: str):
        error = None
        try:
            with s:
                s.send(iter_content(c, 1))
        except RuntimeError as e:
            error = e
        finally:
            assert error is not None

    t = Thread(target=send_data, args=(stream, content))
    t.start()
    with retriever:
        messages = list(retriever.recv())

    assert retriever.closed()
    assert retriever.error() is not None
    assert not stream.alive()
    assert messages[-1] is retriever.error()
    t.join()


def test_new_connection_sync():
    stream, retriever = new_arr_connection(timeout=5, idle=0.2, complete_only=False)
    content = "hello world"

    def send_data(s: Stream, c: str):
        with s:
            s.send(iter_content(c, 0.02))

    send_data(stream, content)
    with retriever:
        messages = list(retriever.recv())
    assert len(messages) == len(content) + 1
    assert messages[len(content)].is_complete()
    assert messages[len(content)].content == content
    assert messages[3].get_seq() == "chunk"


def test_new_connection_wait():
    stream, retriever = new_arr_connection(timeout=5, idle=0.2, complete_only=False)
    content = "hello world"

    def send_data(s: Stream, c: str):
        with s:
            s.send(iter_content(c, 0.02))

    t = Thread(target=send_data, args=(stream, content))
    t.start()
    with retriever:
        retriever.wait()
    t.join()


def test_new_connection_recv_with_sequence():
    stream, retriever = new_arr_connection(timeout=0, idle=0.1, complete_only=False)
    content = "hello world"

    def send_data(s: Stream, c: str):
        with s:
            messages = SequencePipe().across(iter_content(c, 0.02))
            s.send(messages)

    send_data(stream, content)

    got = retriever.recv()
    assert len(list(got)) == len(content) + 1


def test_new_connection_wait_with_sequence():
    stream, retriever = new_arr_connection(timeout=5, idle=0.2, complete_only=False)
    content = "hello world"

    def send_data(s: Stream, c: str):
        with s:
            messages = SequencePipe().across(iter_content(c, 0.02))
            messages = list(messages)
            s.send(messages)

    send_data(stream, content)

    got = retriever.wait()
    assert len(got) == 1


def test_new_connection_with_pool():
    from ghostos.contracts.pool import DefaultPool
    pool = DefaultPool(10)
    stream, retriever = new_arr_connection(timeout=5, idle=0.2, complete_only=False)
    content = "hello world"

    def send_data(s: Stream, c: str):
        with s:
            s.send(iter_content(c, 0.02))

    pool.submit(send_data, stream, content)

    with retriever:
        messages = retriever.wait()
        assert len(messages) == 1
    assert retriever.error() is None
    pool.shutdown(wait=True)
