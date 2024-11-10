from ghostos.prompter import Prompter, GroupPrmt, ParagraphPrmt
from ghostos.container import Container


def test_group_prompters():
    prompter = GroupPrmt(
        title="1"
    ).with_children(
        GroupPrmt(title="1.1"),
        GroupPrmt(title="1.2").with_children(
            GroupPrmt(title="1.2.1"),
            ParagraphPrmt(title="1.2.2", content="hello world"),
        )
    )

    c = Container()
    p = prompter.get_prompt(container=c)
    assert "# 1\n" in p
    assert "\n### 1.2.2\n" in p
