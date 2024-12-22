from ghostos.prompter import (
    TextPrmt, PromptAbleClass, PromptAbleObj, ModelPrompter,
    InspectPrmt,
)
from ghostos.container import Container
import inspect


def test_is_abstract():
    assert inspect.isabstract(PromptAbleObj)
    assert inspect.isabstract(PromptAbleClass)


def test_group_prompters():
    prompter = TextPrmt(
        title="1"
    ).with_children(
        TextPrmt(title="1.1"),
        TextPrmt(title="1.2").with_children(
            TextPrmt(title="1.2.1"),
            TextPrmt(title="1.2.2", content="hello world"),
        )
    )

    c = Container()
    p = prompter.get_prompt(container=c)
    assert "# 1\n" in p
    assert "\n### 1.2.2\n" in p
    # test buffer is ok
    assert p == prompter.get_prompt(c)


def test_inspect_prompters():
    prmt = InspectPrmt()
    prmt.inspect_source(InspectPrmt)
    prmt.inspect_source(test_group_prompters)
    c = Container()
    prompt = prmt.get_prompt(c)
    assert f":{test_group_prompters.__name__}" in prompt


def test_model_prompters():
    class TestPrompter(ModelPrompter):
        line: str = "TestPrompter"

        def self_prompt(self, container: Container) -> str:
            return self.line

        def get_title(self) -> str:
            return ""

    t = TestPrompter()
    assert "TestPrompter" in t.get_prompt(Container())
