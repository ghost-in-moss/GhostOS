from ghostiss.core.ghosts.messenger import DefaultMessenger
from ghostiss.core.runtime.threads import Thread
from ghostiss.core.messages import Message


def test_default_messenger_baseline():
    thread = Thread()
    messenger = DefaultMessenger(thread=thread)
    content = "hello world"
    for c in content:
        msg = Message.new_pack(content=c)
        success = messenger.deliver(msg)
        assert success
    messenger.flush()
    assert len(thread.appending) == 1
    assert thread.appending[0].content == content
