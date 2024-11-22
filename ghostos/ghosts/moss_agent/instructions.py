from ghostos.core.moss import MossRuntime
from ghostos.prompter import Prompter, TextPrmt
from ghostos.identifier import Identifier

AGENT_META_INTRODUCTION = """
You are the mind of an AI Agent driven by `GhostOS` framework.
Here are some basic information you might expect:
"""

GHOSTOS_INTRODUCTION = """
`GhostOS` is an AI Agent framework written in Python, 
providing llm connections, body shell, tools, memory etc and specially the `MOSS` for you.
"""

MOSS_INTRODUCTION = """
You are equipped with the MOSS (Model-oriented Operating System Simulator).
Which provides you a way to control your body / tools / thoughts through Python code.

basic usage: 
1. you will get the python code context that MOSS provide to you below. 
2. you can generate python code to the tool named `moss`, the code will be automatically executed by the outer system.
3. if you print anything in your generated code, the output will be shown in further messages.

the python code you generated, must include a main function, follow the pattern:
```python
def main(moss: Moss):
    \"""
    :param moss: instance of the class `Moss`, the properties on it will be injected with runtime implementations.
    :return: Optional[Operator] 
             if return None, the outer system will perform default action, or observe the values you printed.
             Otherwise, the outer system will execute the operator. 
             You shall only return operator by the libraries provided on `moss`.
    \"""
```
* the outer system will execute the main function in the python module provided to you. you shall not import the module.
* the imported functions are only shown with signature, the source code is omitted.
* if the python code context can not fulfill your will, do not use the `moss` tool.
* you can reply as usual without calling the tool `moss`. use it only when you know what you're doing.
* the code you generated executed only once and do not add to the python context. 
  But the properties on moss instance, will keep existence. 
  You can bind variables of type int/float/bool/str/list/dict/BaseModel to moss instance if you need them for next turn.
"""

MOSS_CONTEXT_TEMPLATE = """
The python context that MOSS provides to you are below:
```python
{code_context}
```
"""

MOSS_FUNCTION_DESC = """
useful to generate execution code of `MOSS`, notice the code must include a `main` function.
"""


def get_moss_context_prompter(title: str, runtime: MossRuntime) -> Prompter:
    code_context = runtime.prompter().dump_code_context()

    injections = runtime.moss_injections()
    children = []
    container = runtime.container()

    for name, injection in injections.items():
        if isinstance(injection, Prompter):
            prompter = TextPrmt(
                title=f"property moss.{name}",
                content=injection.self_prompt(container),
            )
            children.append(prompter)
    end = "more information about attributes on `moss`:" if children else ""
    content = f"""
The module provided to you are `{runtime.module().__name__}`.
The code are:
```python
{code_context}
```

{end}
"""
    return TextPrmt(
        title=title,
        content=content,
    ).with_children(*children)


def get_agent_identity(title: str, id_: Identifier) -> Prompter:
    from ghostos.helpers import yaml_pretty_dump
    value = id_.model_dump(exclude_defaults=True)
    return TextPrmt(
        title=title,
        content=f"""
```yaml
{yaml_pretty_dump(value)}
```
"""
    )
