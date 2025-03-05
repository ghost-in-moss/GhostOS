from ghostos_common.prompter import (
    TextPOM, PromptAbleClass, PromptAbleObj, BasePOM,
    InspectPOM,
)
from ghostos_container import Container
import inspect


def test_is_abstract():
    assert inspect.isabstract(PromptAbleObj)
    assert inspect.isabstract(PromptAbleClass)


def test_group_prompters():
    prompter = TextPOM(
        title="1"
    ).with_children(
        TextPOM(title="1.1"),
        TextPOM(title="1.2").with_children(
            TextPOM(title="1.2.1"),
            TextPOM(title="1.2.2", content="hello world"),
        )
    )

    c = Container()
    p = prompter.get_prompt(container=c)
    assert "# 1\n" in p
    assert "\n### 1.2.2\n" in p
    # test buffer is ok
    assert p == prompter.get_prompt(c)


def test_inspect_prompters():
    prmt = InspectPOM()
    prmt.inspect_source(InspectPOM)
    prmt.inspect_source(test_group_prompters)
    c = Container()
    prompt = prmt.get_prompt(c)
    assert f":{test_group_prompters.__name__}" in prompt


def test_model_prompters():
    class TestPrompter(BasePOM):
        line: str = "TestPrompter"

        def self_prompt(self, container: Container) -> str:
            return self.line

        def get_title(self) -> str:
            return ""

    t = TestPrompter()
    assert "TestPrompter" in t.get_prompt(Container())


def test_pom_with_children():
    t = TextPOM(title="1", content="")
    t.add_child(TextPOM(title="2", content="hello world"))
    c = Container()
    prompt = t.get_prompt(c)
    assert "2" in prompt
