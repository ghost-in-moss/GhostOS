from ghostiss.framework.messengers import DefaultMessenger
from ghostiss.core.runtime.threads import MsgThread
from ghostiss.core.messages import Message
from ghostiss.core.runtime.llms import FunctionalToken


def test_default_messenger_baseline():
    thread = MsgThread()
    messenger = DefaultMessenger(thread=thread)
    content = "hello world"
    for c in content:
        msg = Message.new_pack(content=c)
        success = messenger.deliver(msg)
        assert success
    messenger.flush()
    assert len(thread.appending) == 1
    assert thread.appending[0].content == content


def test_messenger_with_moss():
    functional_tokens = [FunctionalToken(
        token=">moss:",
        name="moss",
        description="desc",
        deliver=False,
    )]

    thread = MsgThread()
    messenger = DefaultMessenger(thread=thread, functional_tokens=functional_tokens)

    contents = ["he", "llo >mo", "ss: w", "orld"]
    content = "".join(contents)
    for c in contents:
        msg = Message.new_pack(content=c)
        messenger.deliver(msg)
    flushed = messenger.flush()
    assert len(list(flushed.callers)) > 0
    message = flushed.messages[0]
    assert message.content != content
    assert message.memory == content
    caller = flushed.callers[0]
    assert caller.name == "moss"
    assert caller.arguments == " world"

    assert len(thread.appending) == 1
    assert len(thread.appending[0].callers) == 1
