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


def test_buffer_sent():
    buffer = DefaultBuffer()
    content = "hello world"
    count = 0
    for c in content:
        msg = Message.new_pack(content=c)
        sent = buffer.buff(msg)
        for i in sent:
            assert not i.is_empty()
            count += 1
    assert count == len(content)


def test_buffer_sent_one_tail():
    buffer = DefaultBuffer()
    content = "hello world"
    tails = 0
    for c in content:
        msg = Message.new_pack(content=c)
        sent = buffer.buff(msg)
        for i in sent:
            if not i.pack:
                tails += 1
    buffed = buffer.flush()
    for i in buffed.unsent:
        if not i.pack:
            tails += 1
    assert tails == 1


def test_buffer_with_moss_token():
    data = '''{
"msg_id": "e28c37c8-4292-4c5e-8c22-25b85fd65af3",
"created": 1722267720.0,
"pack": false,
"content": ""
}'''
    import json
    j = json.loads(data)
    message = Message(**j)
    assert message.content is not None

    buffer = DefaultBuffer(
        functional_tokens=[FunctionalToken(token=">moss:", caller="moss", description="desc", deliver=False)]
    )

    content = "好的，我会帮你播放这首歌。\n\n>moss:\ndef main(os: MOSS) -> Operator:\n    # Search for the song \"七里香\" by 周杰伦\n    song_list = os.player.search(\"\", \"周杰伦\", \"七里香\")\n    \n    # Check if the song is found\n    if \"七里香\" in song_list:\n        # Play the song\n        playing = os.player.play(\"七里香\")\n        \n        # Check if the song is playing\n        if playing:\n            return\n      os.mindflow.finish(\"正在播放周杰伦的《七里香》。\")\n        else:\n            return os.mindflow.fail(\"无法播放周杰伦的《七里香》。\")\n    else:\n        return os.mindflow.fail(\"未找到周杰伦的《七里香》。\")"
    for c in content:
        p = Message.new_pack(content=c)
        buffer.buff(p)
    buffed = buffer.flush()
    assert len(buffed.messages) == 1
    assert len(buffed.callers) == 1


def test_buffer_with_sep_content():
    functional_tokens = [FunctionalToken(
        token=">moss:",
        caller="moss",
        description="desc",
        deliver=False,
    )]

    buffer = DefaultBuffer(functional_tokens=functional_tokens)

    contents = ["he", "llo >mo", "ss: w", "orld"]
    content = "".join(contents)
    for c in contents:
        msg = Message.new_pack(content=c)
        buffer.buff(msg)
    flushed = buffer.flush()
    assert len(flushed.messages) == 1
    assert len(list(flushed.callers)) > 0
    message = flushed.messages[0]
    assert message.content == "hello "
    assert message.memory == content
    caller = flushed.callers[0]
    assert caller.name == "moss"
    assert caller.arguments == " world"

    unsent = list(flushed.unsent)
    assert len(unsent) == 1
    assert unsent[0].content == "hello "
    assert unsent[0].memory == content
    assert len(unsent[0].callers) == 1
