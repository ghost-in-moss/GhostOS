from ghostiss.core.messages import (
    Role,
    Message,
)


def test_text_msg():
    msg = Message.new(role=Role.SYSTEM, content="hello")
    assert msg.content == "hello"
    assert len(msg.msg_id) > 0
    assert msg.created > 0


def test_message_module():
    from ghostiss.core.messages import Message as Msg
    # 不会被重命名而修改掉.
    assert Msg.__name__ == "Message"
    assert Msg.__module__ == "ghostiss.blueprint.messages.message"
