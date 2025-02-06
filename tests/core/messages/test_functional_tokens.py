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
    bad_case1 = """
你好！我将为你运行 `test_entities` 函数。这个函数会测试 `to_entity_meta` 和 `from_entity_meta` 函数的正确性，确保它们能够正确地序列化和反序列化各种类型的对象。

以下是代码执行的结果：

```python
def run(moss):
    test_entities()
    moss.pprint("test_entities 函数执行完毕，所有测试用例均已通过。")
```

<moss>def run(moss):
    test_entities()
    moss.pprint("test_entities 函数执行完毕，所有测试用例均已通过。")
</moss>

运行后，你将看到 `test_entities` 函数的执行结果。如果所有测试用例都通过，你会收到一条成功的信息。如果有任何问题，系统会抛出异常并显示错误信息。
"""

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
        _Case(
            bad_case1,
            "moss",
            True,
            1,
            bad_case1,
            """def run(moss):
    test_entities()
    moss.pprint("test_entities 函数执行完毕，所有测试用例均已通过。")
"""
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
