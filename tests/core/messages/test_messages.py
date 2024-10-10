from ghostos.core.messages import (
    Role,
    Message,
)


def test_text_msg():
    msg = Message.new_done(role=Role.SYSTEM, content="hello")
    assert msg.content == "hello"
    assert len(msg.msg_id) > 0
    assert msg.created > 0


def test_message_module():
    from ghostos.core.messages import Message as Msg
    # 不会被重命名而修改掉.
    assert Msg.__name__ == "Message"
    assert Msg.__module__ == "ghostos.core.messages.message"


def test_message_basic_merge():
    string = "hello world"

    msg = Message.new_head(role="assistant")
    for c in string:
        msg = msg.patch(msg.new_chunk(content=c, role="assistant"))
    assert msg.content == "hello world"


def test_message_with_full_type():
    msg = Message.new_head()
    content = "hello world"
    for c in content:
        msg = msg.patch(msg.new_chunk(content=c))

    last = msg.model_copy(update=dict(content="good"))
    last.chunk = False
    buffed = msg.patch(last)
    assert buffed is not None and buffed.content == "good"


def test_head_is_not_empty():
    msg = Message.new_head()
    assert msg.is_empty()


def test_head_pack_patch():
    msg = Message.new_head(content="a")
    patch = msg.patch(Message.new_chunk(content="b"))
    assert patch is not None
    assert patch.content == "ab"


def test_tail_patch():
    msg = Message.new_head(content="")
    for c in "hello":
        pack = Message.new_chunk(content=c)
        patch = msg.patch(pack)
        assert patch is not None
    tail = Message.new_done(content=" world")
    patch = msg.patch(tail)
    assert patch is None

    tail = Message.new_done(content=" world", msg_id=msg.msg_id)
    patch = msg.patch(tail)
    assert patch is not None
    assert patch.content == " world"


def test_patch_default_type_message():
    msg = Message.new_head(typ_="kind")
    patch = msg.patch(Message.new_chunk(content="c", typ_=""))
    assert patch is not None

    patch = msg.patch(Message.new_chunk(content="c", typ_="kind"))
    assert patch is not None
    pack = Message.new_chunk(content="c", typ_="foo")
    assert pack.type == "foo"
    patch = msg.patch(pack)
    assert patch is None




