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
2. you can generate code by `moss` tool, then the `GhostOS` will execute them for you.
3. if you print anything in your generated code, the output will be shown in further messages.

"""

MOSS_CONTEXT_TEMPLATE = """
The python context `{modulename}` that MOSS provides to you are below:

```python
{code_context}
```

Notices:
* the imported functions are only shown with signature, the source code is omitted.
* the properties on moss instance, will keep existence. 
* You can bind variables of type int/float/bool/str/list/dict/BaseModel to moss instance if you need them for next turn.

You are able to call the `moss` tool, generate code to fulfill your will.
the python code you generated, must include a `run` function, follow the pattern:

```python
def run(moss: Moss):
    \"""
    :param moss: instance of the class `Moss`, the properties on it will be injected with runtime implementations.
    :return: Optional[Operator] 
             if return None, the outer system will perform default action, or observe the values you printed.
             Otherwise, the outer system will execute the operator. 
             You shall only return operator by the libraries provided on `moss`.
    \"""
```

Then the `GhostOS` system will add your code to the python module provided to you, 
and execute the `run` function. 

Notices: 
* Your code will **APPEND** to the code of `{modulename}` then execute, so **DO NOT REPEAT THE DEFINED CODE IN THE MODULE**.
* if the python code context can not fulfill your will, do not use the `moss` tool.
* you can reply as usual without calling the tool `moss`. use it only when you know what you're doing.
* don't copy the main function's __doc__, they are instruction to you only.
* in your code generation, comments is not required, comment only when necessary.
"""

MOSS_FUNCTION_DESC = """
useful to call MOSS system to execute the code. The code must include a `run` function.
"""


def get_moss_context_prompter(title: str, runtime: MossRuntime) -> Prompter:
    code_context = runtime.prompter().dump_module_prompt()

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

    content = MOSS_CONTEXT_TEMPLATE.format(
        modulename=runtime.module().__name__,
        code_context=code_context,
    )

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
