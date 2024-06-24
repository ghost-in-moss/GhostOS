from ghostiss.blueprint.messages import (
    Role,
    TextMsg, ToolMsg, AssistantMsg,
    DefaultTypes,
    first_pack, MessageFactory, Final,
)
from ghostiss.entity import EntityMeta


def test_text_msg():
    msg = TextMsg.new(role=Role.SYSTEM, content="hello")
    assert msg.content == "hello"
    msg = first_pack(msg)
    assert len(msg.msg_id) > 0
    assert msg.created > 0


def test_tool_msg():
    msg = ToolMsg.new(content="tool", tool_call_id="id")
    assert msg.content == "tool"

    items = list(msg.as_openai_memory())
    assert len(items) == 1
    assert items[0]["tool_call_id"] == "id"


def test_message_factory():
    factory = MessageFactory()
    tool = {"type": DefaultTypes.TOOL, "data": {"content": "tool", "tool_call_id": "id"}}
    meta = EntityMeta(**tool)
    tool = factory.new_entity(meta)
    assert isinstance(tool, ToolMsg)
    assert tool.tool_call_id == "id"
    assert tool.role == "tool"


def test_assistant_msg_baseline():
    msg = AssistantMsg.new()
    msg = first_pack(msg)
    assert msg.buff(AssistantMsg.new(content="a"))
    assert msg.content == "a"
    assert msg.buff(AssistantMsg.new(content="b"))
    assert msg.content == "ab"
    assert msg.buff(AssistantMsg.new(content="c"))
    assert msg.content == "abc"

    parse = list(msg.as_openai_message())[0]
    assert parse["content"] == "abc"

    memory = list(msg.as_openai_memory())[0]
    assert memory["content"] == "abc"

    # 通过 reset 重置了 memory 的 content 字段.
    assert msg.buff(AssistantMsg.new(memory="hello", reset=True))
    parse = list(msg.as_openai_message())[0]
    # content 也被重置了.
    assert parse["content"] is None
    assert msg.content is None

    memory = list(msg.as_openai_memory())[0]
    assert memory["content"] == "hello"

    # 确认相关信息存在.
    assert len(msg.msg_id) > 0
    assert msg.created > 0

    # 判断 msg id 不同的影响.
    new_pack = first_pack(AssistantMsg.new(content="new"))
    assert len(new_pack.msg_id) > 0

    # buff 一个新 pack.
    assert not msg.buff(new_pack)
    assert msg.content is None
    assert msg.memory == "hello"

    # 测试 final
    assert not msg.buff(Final())
