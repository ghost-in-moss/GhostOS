from ghostos.framework.messengers import DefaultMessenger
from ghostos.core.messages import Message, new_arr_connection


def test_default_messenger_baseline():
    messenger = DefaultMessenger(None)
    content = "hello world"
    items = []
    for c in content:
        msg = Message.new_chunk(content=c)
        items.append(msg)
    messenger.send(items)
    messages, callers = messenger.flush()
    assert len(messages) == 1
    assert len(callers) == 0


def test_messenger_with_upstream():
    stream, receiver = new_arr_connection()
    messenger = DefaultMessenger(stream)
    items = []
    content = "hello world"
    for c in content:
        msg = Message.new_chunk(content=c)
        items.append(msg)
    with stream:
        messenger.send(items)
        flushed, _ = messenger.flush()
    messages = receiver.wait()
    assert len(flushed) == 1
    assert len(messages) == 1
