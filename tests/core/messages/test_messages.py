from ghostos.core.messages import (
    Role,
    Message, MessageType,
)


def test_text_msg():
    msg = Message.new_tail(role=Role.SYSTEM, content="hello")
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
    last.seq = "complete"
    buffed = msg.patch(last)
    assert buffed is not None and buffed.content == "good"


def test_head_is_not_empty():
    msg = Message.new_head()
    assert msg.is_empty()


def test_message_attrs():
    msg = Message.new_head()
    assert msg.attrs is not None
    msg = Message.new_tail(content="hello world")
    assert msg.attrs is not None


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
    tail = Message.new_tail(content=" world")
    patch = msg.patch(tail)
    assert patch is None

    tail = Message.new_tail(content=" world", msg_id=msg.msg_id)
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


def test_function_call_message():
    head = Message.new_head(
        typ_=MessageType.FUNCTION_CALL,
        call_id="abc",
        name="abc",
    )
    patched = head.patch(
        Message.new_chunk(
            typ_=MessageType.FUNCTION_CALL,
            content="hello world"
        )
    )
    assert patched is not None
    assert patched.call_id == "abc"
    assert patched.name == "abc"
    assert patched.content == "hello world"


def test_message_path_bad_case():
    item1 = Message(msg_id='d5ff6a6a-2b05-4819-864d-82afdf9ac5fc', call_id=None,
                    from_id='chatcmpl-AXs0YM2VxVZbo50C1lIOC0qlWumtN', index=None, type='function_call', stage='',
                    role='assistant', name=None, content='{"', memory=None, attrs={}, payloads={}, callers=[],
                    seq='chunk',
                    created=0.0)
    item2 = Message(msg_id='d5ff6a6a-2b05-4819-864d-82afdf9ac5fc', call_id='call_DCaC3PJy336sZ9ryhxijgFlq',
                    from_id='chatcmpl-AXs0YM2VxVZbo50C1lIOC0qlWumtN', index=None, type='function_call', stage='',
                    role='assistant', name='moss', content='{"', memory=None, attrs={}, payloads={}, callers=[],
                    seq='chunk', created=1732636557.282)
    patched = item1.patch(item2)
    assert patched is not None


def test_message_patch_tail():
    item1 = Message.new_tail(content="hello")
    item2 = Message.new_tail(content="world")
    patched = item1.patch(item2)
    assert patched is None
    assert item1.content == "hello"
    assert item2.content == "world"
