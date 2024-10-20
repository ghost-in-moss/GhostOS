import time

from ghostos.core.messages import Message
from ghostos.framework.streams import new_connection, Stream
from ghostos.framework.messengers import DefaultMessenger
from ghostos.core.session import MsgThread
from ghostos.core.llms import FunctionalToken
from threading import Thread


def test_new_connection_baseline():
    stream, retriever = new_connection(timeout=5, accept_chunks=True)
    content = "hello world, ha ha ha ha"

    def send_data(s: Stream):
        with s:
            for c in content:
                s.deliver(Message.new_chunk(content=c))
                time.sleep(0.1)

    t = Thread(target=send_data, args=(stream,))
    t.start()
    count = 0
    with retriever as items:
        for item in items:
            head = item.head()
            assert head.msg_id
            assert head.chunk
            assert head.content == "h"
            chunks = 0
            for ck in item.chunks():
                assert ck.content == content[chunks]
                chunks += 1
            done = item.done()
            assert done is not None, f"current {count}: {item}"
            assert done.content == content
            count += 1
    assert count == 1


def test_new_connection_timeout():
    stream, retriever = new_connection(timeout=0.2, accept_chunks=True)
    content = "hello world"

    def send_data(s: Stream):
        err = None
        try:
            with s:
                for c in content:
                    s.deliver(Message.new_chunk(content=c))
                    time.sleep(0.5)
        except Exception as e:
            err = e
        assert err is not None

    t = Thread(target=send_data, args=(stream,))
    t.start()
    messages = []
    with retriever as items:
        for item in items:
            done = item.done()
            assert done is not None
            messages.append(done)
    assert len(messages) == 2


def test_new_connection_not_chunks():
    stream, retriever = new_connection(timeout=-1, accept_chunks=True)
    content = "hello world"

    def send_data(s: Stream):
        with s:
            for i in range(5):
                s.deliver(Message.new_tail(content=f"{i}{content}"))
                time.sleep(0.05)

    t = Thread(target=send_data, args=(stream,))
    t.start()
    messages = []
    with retriever as items:
        for item in items:
            head = item.head()
            assert head is not None
            assert head.content.endswith(content)
            assert len(list(item.chunks())) == 1
            done = item.done()
            assert done is not None
            messages.append(done)
    assert len(messages) == 5
    for i in range(len(messages)):
        assert messages[i].content.startswith(str(i))


def test_new_connection_sync():
    stream, retriever = new_connection(timeout=5, accept_chunks=True)
    content = "hello world, ha ha ha ha"

    with stream:
        for c in content:
            stream.deliver(Message.new_chunk(content=c))

    messages = []
    with retriever as items:
        for item in items:
            done = item.done()
            messages.append(done)
    assert len(messages) == 1


def test_new_connection_with_messenger_sync():
    stream, retriever = new_connection(timeout=5, accept_chunks=True)
    content = "hello world, ha ha ha ha"

    with stream:
        messenger = DefaultMessenger(upstream=stream, thread=MsgThread())
        with messenger:
            for c in content:
                messenger.deliver(Message.new_chunk(content=c))

    messages = []
    with retriever as items:
        for item in items:
            done = item.done()
            messages.append(done)
    assert len(messages) == 1


def test_new_connection_with_messenger_async():
    stream, retriever = new_connection(timeout=5, accept_chunks=True)
    content = "hello world, ha ha ha ha"

    def send_data(s: Stream):
        with s:
            messenger = DefaultMessenger(upstream=s, thread=MsgThread())
            with messenger:
                for c in content:
                    messenger.deliver(Message.new_chunk(content=c))
                flushed = messenger.flush()
                assert len(flushed.messages) == 1

    t = Thread(target=send_data, args=(stream,))
    t.start()

    messages = []
    with retriever as items:
        for item in items:
            done = item.done()
            messages.append(done)
    assert len(messages) == 1
    t.join()


def test_new_connection_with_functional_tokens():
    stream, retriever = new_connection(timeout=5, accept_chunks=True)
    content = "hello world<moss>hello</moss>"

    msg_thread = MsgThread()

    def send_data(s: Stream):
        with s:
            messenger = DefaultMessenger(
                upstream=s,
                thread=msg_thread,
                functional_tokens=[
                    FunctionalToken(
                        name="moss",
                        token="<moss>",
                        end_token="</moss>",
                        visible=True,
                    )
                ]
            )
            for c in content:
                messenger.deliver(Message.new_chunk(content=c))
            flushed = messenger.flush()
            assert len(flushed.messages) == 1
            assert len(flushed.callers) == 1
            assert flushed.messages[0].memory is None

    t = Thread(target=send_data, args=(stream,))
    t.start()

    messages = []
    with retriever as items:
        for item in items:
            done = item.done()
            messages.append(done)
    assert len(messages) == 1
    assert len(messages[0].callers) == 1
    assert messages[0].callers[0].arguments == "hello"
    assert len(msg_thread.last_turn().generates[0].callers) == 1
    t.join()
