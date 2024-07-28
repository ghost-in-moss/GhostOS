from typing import Optional, ClassVar
from abc import ABC, abstractmethod
from ghostiss.container import Container
from ghostiss.core.runtime.llms import Chat
from ghostiss.core.messages import FunctionalToken, DefaultTypes
from ghostiss.core.moss import MOSS
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.messenger import Messenger
from ghostiss.core.abc import Identifiable, Identifier
from ghostiss.core.runtime.threads import Thread


class Action(Identifiable, ABC):
    """
    ghost action that triggered by LLM output
    """

    @abstractmethod
    def update_chat(self, chat: Chat) -> Chat:
        pass

    @abstractmethod
    def act(self, container: "Container", messenger: "Messenger", arguments: str) -> Optional["Operator"]:
        """
        """
        pass


DEFAULT_MOSS_FUNCTIONAL_TOKEN = FunctionalToken(
    token=":moss>",
    caller="moss",
    description="""You can output the complete Python code that MOSS is supposed to run after this token. 
The system will automatically execute them.""",
    deliver=False,
)

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

    def __init__(self, moss: MOSS, thread: Thread, functional_token: Optional[FunctionalToken] = None):
        self._moss = moss  # .with_vars()
        self._thread = thread
        if functional_token is None:
            functional_token = DEFAULT_MOSS_FUNCTIONAL_TOKEN.model_copy(deep=True)
        self._functional_token = functional_token

    def identifier(self) -> Identifier:
        return Identifier(
            name="moss",
        )

    def update_chat(self, chat: Chat) -> Chat:
        # update functional tokens
        function_token = self._functional_token
        chat.functional_tokens.append(function_token)

        # update code prompt as system message
        code_prompt = self._moss.dump_code_prompt()
        moss_prompt = DefaultTypes.DEFAULT.new_system(
            content=self.template.format(code=code_prompt),
        )
        chat.system.append(moss_prompt)
        return chat

    def act(self, c: "Container", messenger: "Messenger", arguments: str) -> Optional["Operator"]:
        op = None
        try:
            op = self._moss(code=arguments, target="main", args=["os"])
            if op is not None and not isinstance(op, Operator):
                # todo: 换成正规的异常.
                raise RuntimeError("function main's result is not an instance of the Operator")

            # 运行 moss
            pycontext = self._moss.dump_context()
            content = self._moss.flush()
            # 生成消息并发送.
            message = DefaultTypes.DEFAULT.new_assistant(content=content)
            self._thread.update([message], pycontext)
        except Exception as e:
            # 将异常作为消息. todo: 完善消息.
            content = f"run moss failed: {e}"
            message = DefaultTypes.DEFAULT.new_system(content=content)
            self._thread.update([message])
        return op
