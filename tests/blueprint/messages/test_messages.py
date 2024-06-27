from ghostiss.blueprint.messages import (
    Role,
    Message,
)


def test_text_msg():
    msg = Message.new(role=Role.SYSTEM, content="hello")
    assert msg.content == "hello"
    assert len(msg.msg_id) > 0
    assert msg.created > 0
