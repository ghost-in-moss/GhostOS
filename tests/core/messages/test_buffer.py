from ghostiss.core.messages import (
    DefaultBuffer, Message, FunctionalToken,
)


def test_default_buffer_baseline():
    buffer = DefaultBuffer()
    buffer2 = DefaultBuffer()

    content1 = "hello"
    content2 = "world"

    msg1 = Message.new_head()
    sent = buffer.buff(msg1)
    i = 0
    for item in sent:
        buffer2.buff(item)
        i += 1
    assert i > 0

    for c in content1:
        pack = Message.new_pack(content=c)
        sent = buffer.buff(pack)
        for item in sent:
            buffer2.buff(item)

    buffed = buffer.flush()
    assert len(buffed.messages) == 1
    assert buffed.messages[0].content == content1
    assert buffed.messages[0].memory is None

    new_head = Message.new_head()
    buffer2.buff(new_head)

    for c in content2:
        pack = Message.new_pack(content=c)
        buffer2.buff(pack)

    buffed = buffer2.flush()
    print(buffed)
    assert len(buffed.messages) == 2


def test_functional_token_baseline():
    buffer = DefaultBuffer(
        functional_tokens=[
            FunctionalToken(token=":moss>", caller="moss", description="desc", deliver=False)
        ]
    )

    content = """
hello
:moss>
world
"""

    for c in content:
        msg = Message.new_pack(content=c)
        buffer.buff(msg)

    flushed = buffer.flush()
    assert len(flushed.messages) == 1
    assert len(flushed.callers) == 1
    assert flushed.callers[0].name == "moss"
    assert flushed.callers[0].arguments == "\nworld\n"
    assert flushed.messages[0].content == "\nhello\n"
