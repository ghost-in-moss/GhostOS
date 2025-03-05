from typing import Union, Optional, ClassVar, Dict

from pydantic import BaseModel, Field
from ghostos.abcd.concepts import Operator, Session, Action, SessionPyContext
from ghostos_common.prompter import PromptObjectModel, TextPOM
from ghostos_moss import MossRuntime
from ghostos.core.messages import FunctionCaller
from ghostos.core.llms import (
    Prompt, PromptPipe,
    LLMFunc, FunctionalToken,
)

import json

__all__ = [
    "MossAction", 'MOSS_INTRODUCTION', 'MOSS_FUNCTION_DESC', 'MOSS_CONTEXT_TEMPLATE', 'get_moss_context_pom',
    'get_moss_injections_poms', 'get_moss_injections_poms',
]

MOSS_INTRODUCTION = """
You are equipped with the MOSS (Model-oriented Operating System Simulator).
Which provides you a way to control your body / tools / thoughts through Python code.

basic usage: 
1. you will get the python code context that MOSS provide to you below. 
2. you can generate code with `moss` tool, then the `GhostOS` will execute them for you.
3. if you print anything in your generated code, the output will be shown in further messages.

"""

MOSS_CONTEXT_TEMPLATE = """
The python context `{modulename}` that MOSS provides to you are below:

```python
{source_code}
```

interfaces of some imported attrs are:
```python
{imported_attrs_prompt}
```

{magic_prompt_info}

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
             Otherwise, the outer system will execute the Operator, which is your mindflow operator.
             if some methods return Operator, you can use them to control your mindflow.
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
* You code generation will not modify your provided module's source, unless you got tools to do so.
"""

MOSS_FUNCTION_DESC = ("Useful to execute code in the python context that MOSS provide to you."
                      "The code must include a `run` function.")


class MossAction(Action, PromptPipe):
    DEFAULT_NAME: ClassVar[str] = "moss"

    class Argument(BaseModel):
        code: str = Field(description="the python code you want to execute. never quote them with ```")

    def __init__(self, runtime: MossRuntime, name: str = DEFAULT_NAME):
        self.runtime: MossRuntime = runtime
        self._name = name

    def name(self) -> str:
        return self._name

    def as_function(self) -> Optional[LLMFunc]:
        parameters = self.Argument.model_json_schema()
        llm_func = LLMFunc(
            name=self.name(),
            description=MOSS_FUNCTION_DESC,
            parameters=parameters,
        )
        return llm_func

    def as_functional_token(self) -> FunctionalToken:
        return FunctionalToken.new(
            token=self.name(),
            name=self.name(),
            visible=False,
            desc=MOSS_FUNCTION_DESC,
        )

    def update_prompt(self, prompt: Prompt) -> Prompt:
        llm_func = self.as_function()
        if llm_func is not None:
            prompt.functions.append(llm_func)
        # support functional token as default.
        prompt.functional_tokens.append(self.as_functional_token())
        return prompt

    @classmethod
    def unmarshal_code(cls, arguments: str) -> str:
        try:
            arguments = arguments.strip()
            if arguments.startswith("{"):
                if not arguments.endswith("}"):
                    arguments += "}"
                data = json.loads(arguments)
                args = cls.Argument(**data)
            else:
                args = cls.Argument(code=arguments)
        except Exception:
            args = cls.Argument(code=arguments)
        code = args.code.strip()
        if code.startswith("```python"):
            code = code[len("```python"):]
        if code.startswith("```"):
            code = code[len("```"):]
        if code.endswith("```"):
            code = code[:-len("```")]
        return code.strip()

    def run(self, session: Session, caller: FunctionCaller) -> Union[Operator, None]:
        session.logger.debug("MossAction receive caller: %s", caller)
        # prepare arguments.
        if caller.functional_token:
            code = self.unmarshal_code(caller.arguments)
        else:
            arguments = caller.arguments
            code = self.unmarshal_code(arguments)

        if code.startswith("{") and code.endswith("}"):
            # unmarshal again.
            code = self.unmarshal_code(code)

        # if code is not exists, inform the llm
        if not code:
            return self.fire_error(session, caller, "the moss code is empty")
        session.logger.debug("moss action code: %s", code)

        error = self.runtime.lint_exec_code(code)
        if error:
            return self.fire_error(session, caller, f"the moss code has syntax errors:\n{error}")

        moss = self.runtime.moss()
        try:
            # run the codes.
            result = self.runtime.execute(target="run", code=code, args=[moss])

            # check operator result
            op = result.returns
            if op is not None and not isinstance(op, Operator):
                return self.fire_error(session, caller, "result of moss code is not None or Operator")

            pycontext = result.pycontext
            # rebind pycontext to session
            pycontext = SessionPyContext(**pycontext.model_dump(exclude_defaults=True))
            pycontext.bind(session)

            # handle std output
            std_output = result.std_output
            session.logger.debug("moss action std_output: %s", std_output)
            if std_output:
                output = f"Moss output:\n```text\n{std_output}\n```"
                message = caller.new_output(output)
            else:
                # add empty message since the function output is required.
                message = caller.new_output("moss executed, no std output")
            session.respond([message])
            if op:
                return op
            return session.mindflow().think()

        except Exception as e:
            session.logger.exception(e)
            return self.fire_error(session, caller, f"error during executing moss code: {e}")

    @staticmethod
    def fire_error(session: Session, caller: FunctionCaller, error: str) -> Operator:
        message = caller.new_output("Function Error: %s" % error)
        session.respond([message])
        return session.mindflow().error()


def get_moss_context_pom(title: str, runtime: MossRuntime) -> PromptObjectModel:
    """
    generate prompt from the runtime injections bound to Moss instance.
    :param title:
    :param runtime:
    :return:
    """
    prompter = runtime.prompter()
    source_code = prompter.get_source_code()
    imported_attrs_prompt = prompter.get_imported_attrs_prompt([Operator])
    magic_prompt = prompter.get_magic_prompt()
    magic_prompt_info = ""
    if magic_prompt:
        magic_prompt_info = f"more information about the module:\n```text\n{magic_prompt}\n```\n"

    injections = runtime.moss_injections()
    children = []
    container = runtime.container()

    for name, injection in injections.items():
        if isinstance(injection, PromptObjectModel):
            prompter = TextPOM(
                title=f"property `moss.{name}`",
                content=injection.get_prompt(container),
            )
            children.append(prompter)

    content = MOSS_CONTEXT_TEMPLATE.format(
        modulename=runtime.module().__name__,
        source_code=source_code,
        imported_attrs_prompt=imported_attrs_prompt,
        magic_prompt_info=magic_prompt_info,
    )

    return TextPOM(
        title=title,
        content=content,
    ).with_children(*children)


def get_moss_injections_poms(runtime: MossRuntime) -> Dict[str, PromptObjectModel]:
    poms = {}
    injections = runtime.moss_injections()
    for name, injection in injections.items():
        if isinstance(injection, PromptObjectModel):
            poms[name] = injection
    return poms


def get_moss_injections_poms_prompt(runtime: MossRuntime) -> str:
    container = runtime.container()
    children = []
    # replace the pom title.
    for name, pom in get_moss_injections_poms(runtime).items():
        children.append(TextPOM(
            title=f"moss.{name}",
            content=pom.self_prompt(container),
        ))

    prompter = TextPOM(
        title="Moss Injections",
    ).with_children(*children)
    return prompter.get_prompt(container)
