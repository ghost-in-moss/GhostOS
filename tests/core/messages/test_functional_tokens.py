from ghostos.core.messages import Message
from ghostos.core.messages.pipeline import SequencePipe, run_pipeline
from ghostos.core.messages.functional_tokens import XMLFunctionalTokenPipe
from ghostos.core.llms.tools import FunctionalToken


def test_xml_functional_token_pipe_baseline():
    content = "hello<moss>test</moss>world"

    ft = FunctionalToken.new(
        token="moss",
    )
    sequence_pipe = SequencePipe()
    xml_ft_pipe = XMLFunctionalTokenPipe([ft])

    messages = []
    for c in content:
        messages.append(Message.new_chunk(content=c))

    items = list(run_pipeline([sequence_pipe, xml_ft_pipe], messages))
    last = items[-1]
    assert last.is_complete()
    assert len(last.callers) == 1
    caller = last.callers[0]
    assert caller.name == "moss"
    assert caller.functional_token
    assert caller.arguments == "test"


def test_2_xml_functional_token_pipe():
    content = "hello<moss>test</moss>world<test>test</test>"

    ft1 = FunctionalToken.new(
        token="moss",
        visible=False,
    )
    ft2 = FunctionalToken.new(
        token="test",
    )
    sequence_pipe = SequencePipe()
    xml_ft_pipe = XMLFunctionalTokenPipe([ft1, ft2])

    messages = []
    for c in content:
        messages.append(Message.new_chunk(content=c))

    items = list(run_pipeline([sequence_pipe, xml_ft_pipe], messages))
    last = items[-1]
    assert last.is_complete()
    assert len(last.callers) == 2
    assert last.memory == content
    assert last.content == "helloworld<test>test</test>"


def test_xml_functional_token_pipe_cases():
    from typing import NamedTuple, List

    class _Case(NamedTuple):
        content: str
        token: str
        visible: bool
        caller_count: int
        output_content: str
        arguments: str

    cases: List[_Case] = [
        _Case(
            "helloworld",
            "moss",
            True,
            0,
            "",
            "",
        ),
        _Case(
            "hello<moss>test</moss>world",
            "moss",
            True,
            1,
            "hello<moss>test</moss>world",
            "test",
        ),
        _Case(
            "hello<moss>test</moss world",
            "moss",
            True,
            0,
            "",
            "",
        ),
        _Case(
            "hello<moss>test world",
            "moss",
            True,
            0,
            "",
            "",
        ),
        _Case(
            "hello</moss>test world",
            "moss",
            True,
            0,
            "",
            "",
        ),
        _Case(
            "hello<moss>test</moss> world",
            "moss",
            False,
            0,
            "hello world",
            "test",
        ),
        _Case(
            "hello<moss>test1</moss> world <moss>test2</moss>",
            "moss",
            False,
            1,
            "hello world <moss>test2</moss>",
            "test1",
        ),

    ]

    for c in cases:
        messages = []
        for char in c.content:
            messages.append(Message.new_chunk(content=char))

        ft = FunctionalToken.new(token=c.token, visible=c.visible)
        sequence_pipe = SequencePipe()
        xml_ft_pipe = XMLFunctionalTokenPipe([ft])
        items = list(run_pipeline([sequence_pipe, xml_ft_pipe], messages))
        last = items[-1]
        assert last.is_complete()
        if c.caller_count > 0:
            assert len(last.callers) == c.caller_count
            caller = last.callers[0]
            assert caller.name == c.token, repr(c)
            assert caller.arguments == c.arguments, repr(c)
            assert last.content == c.output_content, repr(c)
