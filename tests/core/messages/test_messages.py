from ghostiss.core.messages import (
    Role,
    Message,
)


def test_text_msg():
    msg = Message.new_tail(role=Role.SYSTEM, content="hello")
    assert msg.content == "hello"
    assert len(msg.msg_id) > 0
    assert msg.created > 0


def test_message_module():
    from ghostiss.core.messages import Message as Msg
    # 不会被重命名而修改掉.
    assert Msg.__name__ == "Message"
    assert Msg.__module__ == "ghostiss.core.messages.message"


def test_message_basic_merge():
    string = "hello world"

    msg = Message.new_head(role="assistant")
    for c in string:
        msg = msg.patch(msg.new_pack(content=c, role="assistant"))
    assert msg.content == "hello world"


def test_message_with_full_type():
    msg = Message.new_head()
    content = "hello world"
    for c in content:
        msg = msg.patch(msg.new_pack(content=c))

    last = msg.model_copy(update=dict(content="good"))
    last.pack = False
    buffed = msg.patch(last)
    assert buffed is not None and buffed.content == "good"


def test_head_is_not_empty():
    msg = Message.new_head()
    assert not msg.is_empty()
