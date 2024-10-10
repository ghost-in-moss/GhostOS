from ghostos.framework.messengers import Messenger, DefaultMessenger
from ghostos.core.session.threads import MsgThread
from ghostos.core.messages import Message
from ghostos.core.llms import FunctionalToken
import time


def test_default_messenger_baseline():
    thread = MsgThread()
    messenger = DefaultMessenger(thread=thread)
    content = "hello world"
    for c in content:
        msg = Message.new_chunk(content=c)
        success = messenger.deliver(msg)
        assert success
    messenger.flush()
    assert len(thread.current.generates) == 1
    assert thread.current.generates[0].content == content


def test_messenger_with_moss_xml_token():
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
        msg = Message.new_chunk(content=c)
        messenger.deliver(msg)
    flushed = messenger.flush()
    assert len(list(flushed.callers)) > 0
    message = flushed.messages[0]
    assert message.content != content
    assert message.memory == content
    caller = flushed.callers[0]
    assert caller.name == "moss"
    assert caller.arguments == " world"

    assert len(thread.current.generates) == 1
    assert len(thread.current.generates[0].callers) == 1


def test_messenger_with_single_message():
    functional_tokens = [FunctionalToken(
        token="<moss>",
        end_token="</moss>",
        name="moss",
        description="desc",
        deliver=False,
    )]

    thread = MsgThread()
    messenger = DefaultMessenger(thread=thread, functional_tokens=functional_tokens)

    content = "<moss>def main():\n    pass</moss>"
    messenger.say(content)
    flushed = messenger.flush()
    assert flushed.messages[0].content == ""
    assert flushed.messages[0].memory == content
    assert len(flushed.callers) == 1

# def test_async_sub_messengers():
#     from threading import Thread
#     functional_tokens = [FunctionalToken(
#         token="<moss>",
#         end_token="</moss>",
#         name="moss",
#         description="desc",
#         deliver=False,
#     )]
#
#     def make(m: Messenger, idx: int):
#         def fn():
#             content = f"{idx}<moss>def main():\n    pass</moss>"
#             mod = idx % 3 + 1
#             contents = []
#             c = 0
#             while c < len(content):
#                 contents.append(content[c:c + mod])
#                 c = c + mod
#             for line in contents:
#                 m.deliver(Message.new_chunk(content=line))
#                 time.sleep(0.1)
#             messages, callers = m.flush()
#             print(f"\ncontent {idx}: {len(messages)} + `{messages[0].content}`")
#
#
#         return fn
#
#     thread = MsgThread()
#     messenger = DefaultMessenger(thread=thread, functional_tokens=functional_tokens)
#     running = []
#     for i in range(10):
#         sub = messenger.new()
#         f = make(sub, i)
#         t = Thread(target=f)
#         running.append(t)
#         t.start()
#     for t in running:
#         t.join()
#     flushed = messenger.flush()
#     for msg in flushed.messages:
#         # print(msg.streaming_id)
#         print("\n++\n" + msg.get_content())
#     for caller in flushed.callers:
#         print(caller.arguments)
