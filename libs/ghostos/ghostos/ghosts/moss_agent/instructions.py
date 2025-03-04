from ghostos_common.prompter import PromptObjectModel, TextPOM
from ghostos_common.identifier import Identifier

AGENT_META_INTRODUCTION = """
<!Private not visible to user!>
You are the mind of an AI Agent driven by `GhostOS` framework.
Here are some basic information you might expect:
"""

GHOSTOS_INTRODUCTION = """
`GhostOS` is an AI Agent framework written in Python, 
providing llm connections, body shell, tools, memory etc and specially the `MOSS` protocol for you.
"""


def get_agent_identity(title: str, id_: Identifier) -> PromptObjectModel:
    from ghostos_common.helpers import yaml_pretty_dump
    value = id_.model_dump(exclude_defaults=True)
    return TextPOM(
        title=title,
        content=f"""
```yaml
{yaml_pretty_dump(value)}
```
"""
    )
