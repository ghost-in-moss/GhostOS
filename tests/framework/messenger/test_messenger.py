from ghostos.framework.messengers import DefaultMessenger
from ghostos.core.messages import Message, new_basic_connection, MessageType, ReceiverBuffer


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
    stream, receiver = new_basic_connection()
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


def test_messenger_with_function_call():
    stream, receiver = new_basic_connection()
    messenger = DefaultMessenger(stream)
    items = []
    content = "hello world"
    for c in content:
        msg = Message.new_chunk(content=c)
        items.append(msg)
    for c in content:
        msg = Message.new_chunk(content=c, typ_=MessageType.FUNCTION_CALL, call_id="123", name="good")
        items.append(msg)
    with stream:
        messenger.send(items)
        flushed, callers = messenger.flush()
        assert len(flushed) == 2
    assert len(callers) == 1
    with receiver:
        buffer = ReceiverBuffer.new(receiver.recv())
        assert MessageType.is_text(buffer.head())
        assert len(list(buffer.chunks())) == len(content)
        buffer = buffer.next()
        assert MessageType.FUNCTION_CALL.match(buffer.head())
        assert len(list(buffer.chunks())) == len(content)
        assert buffer.next() is None
