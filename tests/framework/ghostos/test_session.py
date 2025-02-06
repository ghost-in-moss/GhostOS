from ghostos.framework.messengers import DefaultMessenger
from ghostos.core.runtime.threads import GoThreadInfo
from ghostos.core.messages import Message
from threading import Lock, Thread


def test_thread_sending_message_with_stage():
    thread = GoThreadInfo.new(None)
    lock = Lock()

    def send_thread(content: str, stage: str):
        items = []
        for c in content:
            msg = Message.new_chunk(content=c)
            items.append(msg)
        messenger = DefaultMessenger(None, stage=stage)
        messenger.send(items)
        messages, callers = messenger.flush()
        with lock:
            thread.append(*messages)

    cases = [
        ("hello world1", ""),
        ("hello world2", "a"),
        ("hello world3", "a"),
        ("hello world4", "b"),
        ("hello world5", ""),
    ]

    run = []
    for c in cases:
        t = Thread(target=send_thread, args=c)
        t.start()
        run.append(t)

    for t in run:
        t.join()

    assert len(thread.last_turn().added) == 5
    for message in thread.last_turn().added:
        assert message.content.startswith("hello world")

    thread.new_turn(None)
    prompt = thread.to_prompt([], [""])
    assert len(prompt.history) == 2
    prompt = thread.to_prompt([], ["a", "b"])
    assert len(prompt.history) == 3

