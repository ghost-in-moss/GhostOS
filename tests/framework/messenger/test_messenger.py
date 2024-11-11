from ghostos.framework.messengers import DefaultMessenger
from ghostos.core.messages import Message


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
