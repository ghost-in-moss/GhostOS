from typing import Optional, TYPE_CHECKING, ClassVar
from abc import ABC, abstractmethod
from ghostiss.core.runtime.llms import LLMTool, Chat
from ghostiss.core.messages import FunctionalToken, DefaultTypes
from ghostiss.core.moss import MOSS

if TYPE_CHECKING:
    from ghostiss.core.ghosts._ghost import Ghost
    from ghostiss.core.ghosts.operators import Operator


class Action(ABC):
    """
    ghost action that triggered by LLM output
    """

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def update_chat(self, chat: Chat) -> Chat:
        pass

    @abstractmethod
    def act(self, g: "Ghost", arguments: str) -> Optional["Operator"]:
        pass


class MOSSAction(Action):
    """
    系统内置的 MOSS Action.
    """

    template: ClassVar[str] = """
# MOSS 

You are in a Model-oriented Operating System (MOSS) mode. 
With moss you can use python code to 

You are tasked to generate a single block of Python code that defines a function `def main(os: MOSS) -> Operator:`. 

**Directives for Your Task**:
- **Code Generation Only**: Produce a block of Python code for the `main` function. The interface, class and abstract methods in context are ALREADY implemented in external system, and passed into main as arguments, DON'T implement them or instantiate them again, just invoke them directly on you need.
- **Format Requirement**: Your output must be a single block of Python code enclosed within triple backticks. Do not include any additional text, comments, or explanations outside this code block. Do not invoke main method by yourself.

**External System Responsibilities**:
- **Execution and Data Fetching**: The external system will concatenate your code with the true context (implemented all abstract methods and interface), execution the main method and wait to fetch the result.
- **Result Handling**: The external system will process the results and manage user interactions.


Here is the context provided to you in this turn:

```python
{code}
```
"""

    def __init__(self, moss: MOSS):
        self._moss = moss  # .with_vars()

    def name(self) -> str:
        return "moss"

    def update_chat(self, chat: Chat) -> Chat:
        # update functional tokens
        function_token = FunctionalToken(
            token=":moss>",
            caller="moss",
            description="",
            deliver=False,
        )
        chat.functional_tokens.append(function_token)

        # update code prompt as system message
        code_prompt = self._moss.dump_code_prompt()
        moss_prompt = DefaultTypes.DEFAULT.new_system(
            content=self.template.format(code=code_prompt),
        )
        chat.system.append(moss_prompt)
        return chat

    def act(self, g: "Ghost", arguments: str) -> Optional["Operator"]:
        op = self._moss(code=arguments, target="main", args=["os"])
        if op is not None and not isinstance(op, Operator):
            # todo: 换成正规的异常.
            raise RuntimeError("Operator is not an operator.")

        # 运行 moss
        pycontext = self._moss.dump_context()
        content = self._moss.flush()
        # 生成消息并发送.
        message = DefaultTypes.DEFAULT.new_assistant(content=content)

        # 准备发送消息.
        messenger = g.messenger()
        messenger.deliver(message)
        delivered, _ = messenger.flush()

        # 更新 thread.
        session = g.session
        # 更新消息.
        thread = session.thread()
        thread.update(delivered, pycontext)
        session.update_thread(thread)
        # 返回结果.
        return op
