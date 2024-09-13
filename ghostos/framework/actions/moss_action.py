import json

from typing import Optional, ClassVar
from ghostos.container import Container
from ghostos.core.ghosts import Action, Ghost
from ghostos.core.llms import Chat, FunctionalToken
from ghostos.core.messages import DefaultMessageTypes, Caller
from ghostos.core.moss import MossRuntime, moss_message
from ghostos.core.ghosts.operators import Operator
from ghostos.core.session import Session
from ghostos.abc import Identifier
from pydantic import BaseModel, Field
from traceback import format_exc

__all__ = ['MossAction', 'MossArgument', 'DEFAULT_MOSS_FUNCTIONAL_TOKEN']


class MossArgument(BaseModel):
    code: str = Field(description="generate python code which will be executed by Moss")


DEFAULT_MOSS_FUNCTIONAL_TOKEN = FunctionalToken(
    token="<moss>",
    end_token="</moss>",
    name="moss",
    description="""
You can output the Python code that MOSS is supposed to run after this token. 
The system will automatically execute them. 
include `def main(os: Moss) -> Operator`
Notice:
- You are only able to generate MOSS code within this token.
- The content within this token shall be Python code only. 
- You can send anything directly before this token, not after it.
- **Never** use ``` to embrace your code.
- Need not to mention the code you generated to user.
""".strip(),
    visible=False,
    parameters=MossArgument.model_json_schema(),
)


class MossAction(Action):
    """
    系统内置的 MOSS Action, 同步运行.
    """

    template: ClassVar[str] = """
# MOSS 

You are equipped with the MOSS (Model-oriented Operating System Simulation) that provides tools and thought directions 
in python interface.
With MOSS you shall generate a single block of Python code,
in which must define a function `main(moss: Moss) -> Optional[Operator]:`, 
the MOSS will automatically execute the main function. 

About main function parameters: 
```
:param moss: instance of Moss that has been injected with dependencies.
:return: return Operator by existing library, or return None to take default action. NEVER define it by yourself.
```


**Directives for MOSS**:
- **Code Generation Only**: Produce a block of Python code for the `main` function. 
  The interface, class and abstract methods in context are ALREADY implemented in external system, 
  and passed into main as arguments, DON'T implement them or instantiate them again, 
  just invoke them directly on you need.
- **Format Requirement**: Your output must be a single block of Python code enclosed within triple backticks. 
  Do not include any additional text, comments, or explanations outside this code block. 
  Do not invoke main method by yourself.

**External System Responsibilities**:
- **Execution and Data Fetching**: The external system will concatenate your code with the true context 
  (implemented all abstract methods and interface), execution the main method and wait to fetch the result.
- **Result Handling**: The external system will process the results and manage user interactions. 
  Std output will be buffed by MOSS, you can generate operator to observe them.


Here is the context provided to you in this turn:

```python
{code}
```

**Notices**
0. You need not to use MOSS when you don't need it such like sending raw text or using other tools.
1. MOSS is a private system only serve for you, **never mention it existence**.
2. MOSS code shall be generated within functional token, markdown python block will not do, and **don't repeat the code with markdown**.
3. MOSS will automatic execute the main function so you never execute it again.
4. **Return Operator**: You shall always use method that MOSS provide you to return an Operator from function main. 
5. In the generated MOSS code, ** YOU SHALL NOT WRITE ANYTHING BUT CODE AND COMMENTS BECAUSE MOSS CODE NEVER SEND TO USER**.

**About Coding Jobs**: 
Sometimes you are handling coding task, the MOSS provides you code interface to handle your job.
But the MOSS code you generated is not the target code you are coding. DO NOT CONFUSE THE Them!
At these scenarios you shall write target code as string, and using the libraries MOSS providing to you to handle them.
"""

    def __init__(
            self,
            moss_runtime: MossRuntime,
            functional_token: Optional[FunctionalToken] = None,
            deliver: bool = False,
    ):
        self._moss_runtime = moss_runtime
        if functional_token is None:
            functional_token = DEFAULT_MOSS_FUNCTIONAL_TOKEN.model_copy(deep=True)
        functional_token.visible = deliver
        self._functional_token = functional_token

    def identifier(self) -> Identifier:
        return Identifier(
            name=self._functional_token.name,
            description=self._functional_token.description,
        )

    def prepare_chat(self, chat: Chat) -> Chat:
        # update functional tokens
        function_token = self._functional_token
        chat.functional_tokens.append(function_token)

        # update code prompt as system message
        code_prompt = self._moss_runtime.prompter().dump_context_prompt()
        moss_instruction = self.template.format(code=code_prompt)
        moss_prompt = DefaultMessageTypes.DEFAULT.new_system(
            content=moss_instruction,
        )
        chat.system.append(moss_prompt)
        return chat

    def act(self, c: "Container", session: Session, caller: Caller) -> Optional["Operator"]:
        thread = session.thread()
        op = None
        if caller.functional_token:
            code = caller.arguments
        else:
            unmarshal = json.loads(caller.arguments)
            argument = MossArgument(**unmarshal)
            code = argument.code

        messenger = session.messenger(thread=thread)
        code = code.rstrip().replace("```python", "").replace("```", "")
        try:
            executed = self._moss_runtime.execute(code=code, target="main", local_args=["moss"])
            op = executed.returns
            if op is not None and not isinstance(op, Operator):
                # todo: 换成正规的异常.
                raise RuntimeError("function main's result is not an instance of the Operator")

            # 运行 moss
            pycontext = executed.pycontext
            printed = executed.std_output
            content = ""
            if printed:
                content = f"printed content (only visible to you): \n {printed}"
            # 生成消息并发送.
            if content:
                # 理论上对用户不展示的消息.
                message = moss_message(content="", memory=content)
                messenger.deliver(message)
                thread.update_pycontext(pycontext)
            if content and op is None:
                op = c.force_fetch(Ghost).taskflow().think()
        except Exception as e:
            # 将异常作为消息. todo: 完善消息.
            content = f"run moss failed: \n{e} \n\n{format_exc()}"
            message = moss_message(content="", memory=content)
            messenger.deliver(message)
            op = c.force_fetch(Ghost).taskflow().think()
        finally:
            # 将 moss 清空掉.
            self._moss_runtime.destroy()
            session.update_thread(thread, False)
        return op
