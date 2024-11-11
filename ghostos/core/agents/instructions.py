from ghostos.core.moss import MossRuntime
from ghostos.prompter import Prompter, TextPrmt
from ghostos.identifier import Identifier

AGENT_INTRODUCTION = """
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
    :return: Union[Operator, None], if None, the outer system will perform default action. 
             Otherwise, the outer system will execute the operator. 
             You shall only return operator by the libraries provided by `moss`.
    \"""
```

* the outer system will execute the main function to realize your will.
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
    return TextPrmt(
        title=title,
        content=code_context,
    ).with_children(*children)


def get_agent_identity(title: str, id_: Identifier) -> Prompter:
    return TextPrmt(
        title=title,
        content=f"""
`name`: 
{id_.name}

`description`: 
{id_.description}
"""
    )
