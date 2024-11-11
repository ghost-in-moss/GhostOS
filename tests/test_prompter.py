from ghostos.prompter import TextPrmt, PromptAbleClass, PromptAbleObj
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
    assert prompter.__children__ is None
