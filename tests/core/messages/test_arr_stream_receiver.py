from typing import Iterable
from ghostos.core.messages.transport import new_basic_connection, Stream, ReceiverBuffer
from ghostos.core.messages.pipeline import SequencePipe
from ghostos.core.messages.message import Message, MessageType
from threading import Thread
import time


def iter_content(content: str, gap: float) -> Iterable[Message]:
    for c in content:
        item = Message.new_chunk(content=c)
        yield item
        if gap > 0:
            time.sleep(gap)


def test_new_connection_baseline():
    stream, retriever = new_basic_connection(timeout=5, idle=0.2, complete_only=False)
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
    stream, retriever = new_basic_connection(timeout=5, idle=0.2, complete_only=True)
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
    stream, retriever = new_basic_connection(timeout=0.2, idle=0.2, complete_only=False)
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
    stream, retriever = new_basic_connection(timeout=5, idle=0.2, complete_only=False)
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
    stream, retriever = new_basic_connection(timeout=5, idle=0.2, complete_only=False)
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
    stream, retriever = new_basic_connection(timeout=0, idle=0.1, complete_only=False)
    content = "hello world"

    def send_data(s: Stream, c: str):
        with s:
            messages = SequencePipe().across(iter_content(c, 0.02))
            s.send(messages)

    send_data(stream, content)

    got = retriever.recv()
    assert len(list(got)) == len(content) + 1


def test_new_connection_wait_with_sequence():
    stream, retriever = new_basic_connection(timeout=5, idle=0.2, complete_only=False)
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
    stream, retriever = new_basic_connection(timeout=5, idle=0.2, complete_only=False)
    content = "hello world"

    def send_data(s: Stream, c: str):
        with s:
            s.send(iter_content(c, 0.02))
            s.send(iter_content(c, 0.02))

    pool.submit(send_data, stream, content)

    with retriever:
        messages = retriever.wait()
        assert len(messages) == 2
    assert retriever.error() is None
    pool.shutdown(wait=True)


def test_array_receiver_buffer_baseline():
    stream, retriever = new_basic_connection(timeout=5, idle=0.2, complete_only=False)
    content = "hello world"

    def send_data(s: Stream, c: str):
        messages = SequencePipe().across(iter_content(c, 0))
        messages = list(messages)
        s.send(messages)

    with stream:
        send_data(stream, content)
        send_data(stream, content)

    buffer = ReceiverBuffer.new(retriever.recv())
    assert buffer is not None
    assert buffer.head().content == "h"
    for chunk in buffer.chunks():
        assert chunk.content in content
        assert len(chunk.content) == 1
        assert not chunk.is_complete()

    assert buffer.tail().content == content
    assert buffer.tail().is_complete()
    buffer = buffer.next()
    assert buffer is not None
    assert buffer.head().content == "h"
    assert buffer.tail().content == content

    buffer = buffer.next()
    assert buffer is None


def test_array_receiver_buffer_async():
    from ghostos.contracts.pool import DefaultPool
    pool = DefaultPool(10)
    stream, retriever = new_basic_connection(timeout=5, idle=0.2, complete_only=False)
    content = "hello world"

    def send_data(s: Stream, c: str):
        with s:
            s.send(iter_content(c, 0.02))
            s.send(iter_content(c, 0.02))

    pool.submit(send_data, stream, content)

    with retriever:
        buffer = ReceiverBuffer.new(retriever.recv())
        assert buffer.tail().content == content
        buffer = buffer.next()
        assert buffer.tail().content == content
        buffer = buffer.next()
        assert buffer is None
    pool.shutdown(wait=True)


def test_array_receiver_with_error():
    stream, retriever = new_basic_connection(timeout=5, idle=0.2, complete_only=False)
    content = "hello world"

    def send_data(s: Stream, c: str):
        with s:
            s.send(iter_content(c, 0.02))
            s.send([MessageType.ERROR.new(content="error")])

    send_data(stream, content)
    with retriever:
        messages = retriever.wait()
    assert len(messages) == 2
    assert messages[1].is_complete()
    assert messages[1].type == MessageType.ERROR


def test_array_receiver_bad_case_1():
    item = Message(
        msg_id='25c6d3d9-9bb1-45e1-ac7e-585380975ea1',
        call_id='call_SyYPOCVP60bvyLIMP3gemVYy',
        index=None,
        type='function_call',
        stage='',
        role='assistant',
        name='moss',
        content='',
        memory=None,
        attrs={},
        payloads={'task_info': {'task_id': '8d98d7772baa6776c7a169ef2028c06a', 'task_name': 'SpheroGPT',
                                'process_id': '7167a681-cc2e-43aa-aab8-1781f9308e3f',
                                'shell_id': 'ghostos_streamlit_app', 'thread_id': '8d98d7772baa6776c7a169ef2028c06a'}},
        callers=[],
        seq='chunk',
        created=1732633767.653,
    )
    item2 = Message(
        **{
            "msg_id": "",
            "call_id": None,
            "index": None,
            "type": "function_call",
            "stage": "",
            "role": "assistant",
            "name": "SpheroGPT",
            "content": "os",
            "memory": None,
            "attrs": {},
            "payloads": {},
            "callers": [],
            "seq": "chunk",
            "created": 0.0,
        })

    patched = item.patch(item2)
    assert patched is not None
    assert patched.name == "moss"


def test_receiver_with_stages():
    stream, retriever = new_basic_connection(timeout=5, idle=0.2, complete_only=False)

    def send_data(s: Stream):
        with s:
            s.send([
                Message.new_tail(content="test1", stage="reasoning"),
                Message.new_tail(content="test2"),
            ])

    send_data(stream)

    with retriever:
        items = list(retriever.recv())
        assert len(items) == 2


def test_receiver_buffers_with_stages():
    stream, retriever = new_basic_connection(timeout=5, idle=0.2, complete_only=False)

    def send_data(s: Stream):
        with s:
            s.send([
                Message.new_tail(content="test", stage="reasoning"),
                Message.new_tail(content="test"),
            ])

    send_data(stream)

    with retriever:
        buffer = ReceiverBuffer.new(retriever.recv())
        assert buffer is not None
        assert buffer.tail().stage == "reasoning"
        buffer = buffer.next()
        assert buffer is not None
        assert buffer.tail().stage == ""
