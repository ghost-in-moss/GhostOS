from typing import Tuple, Optional, List
from abc import ABC, abstractmethod

from ghostos.abc import Identifier
from ghostos.core.llms import Chat, LLMApi
from ghostos.core.quests.itf import QuestAction, QuestOperator
from ghostos.core.quests.steps import ObserveOperator
from ghostos.core.quests.drivers import LLMQuestDriver
from ghostos.core.moss import (
    PyContext, MossCompiler, DEFAULT_MOSS_FUNCTIONAL_TOKEN
)
from ghostos.container import Container
from ghostos.core.session import MsgThread, DefaultEventType
from ghostos.core.messages import Role, Caller, Message

DEFAULT_MOSS_PROMPT_TEMPLATE = """
# MOSS 

You are equipped with the MOSS (Model-oriented Operating System) that provides tools and thought directions in python interface.
With MOSS you shall generate a single block of Python code in which defines a function `def main(os: MOSS) -> Step:`, 
the MOSS will automatically execute them. 

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
0. You need not to use MOSS when you don't need it's api such as tell raw text or use other functional tokens.
1. MOSS is a private system only serve for you, **never mention it existence**.
2. MOSS code shall be generated within functional token, markdown python block will not do, and **don't repeat the code with markdown**.
3. MOSS will automatic execute the main function so you never execute it again.
4. **Return Operator**: You shall always use method that MOSS provide you to return an Operator from function main. 
5. In the generated MOSS code, ** YOU SHALL NOT WRITE ANYTHING BUT CODE AND COMMENTS BECAUSE MOSS CODE NEVER SEND TO USER**.
6. Your generated code must include `def main(os: MOSS) -> Operator` method which will be executed following your intention. 
"""


class MossQuestAction(QuestAction):
    """
    Moss 的 QuestAction 封装.
    """

    def __init__(self, compiler: MossCompiler, thread: MsgThread):
        compiler = compiler.join_context(thread.get_pycontext())
        moss_runtime = compiler.compile('__quest__')
        self.moss_runtime = moss_runtime

    def prepare_chat(self, chat: Chat) -> Chat:
        code_prompt = self.moss_runtime.prompter().dump_context_prompt()
        system_prompt = DEFAULT_MOSS_PROMPT_TEMPLATE.format(code=code_prompt)
        system_message = Role.SYSTEM.new(content=system_prompt)
        chat.system.append(system_message)
        chat.functional_tokens.append(DEFAULT_MOSS_FUNCTIONAL_TOKEN)
        return chat

    def identifier(self) -> Identifier:
        return DEFAULT_MOSS_FUNCTIONAL_TOKEN.identifier()

    def callback(self, thread: MsgThread, caller: Caller) -> Tuple[MsgThread, Optional[QuestOperator]]:
        step = self.moss_runtime.execute(
            target='main',
            code=caller.arguments,
            local_args=['moss']
        )
        if step is not None and not isinstance(step, QuestOperator):
            message = Role.SYSTEM.new(content="main function returns is not instance of Step")
            return thread, ObserveOperator([message])

        thread = thread.update_history()
        pycontext = self.moss_runtime.dump_pycontext()
        content = self.moss_runtime.dump_std_output()
        message = Role.SYSTEM.new(content="moss std output:\n" + content)
        thread.append()
        thread.new_turn(
            DefaultEventType.THINK.new(
                task_id=thread.id,
                from_task_id=thread.id,
                messages=[message],
            ),
            pycontext=pycontext,
        )
        return thread, step


class MossQuestDriver(LLMQuestDriver, ABC):
    """
    Moss 的驱动.
    """

    @abstractmethod
    def system_messages(self) -> List[Message]:
        pass

    @abstractmethod
    def get_llm_api(self, container: Container) -> LLMApi:
        pass

    @abstractmethod
    def init(self) -> MsgThread:
        pass

    def actions(self, container: Container, thread: MsgThread) -> List[QuestAction]:
        """
        所有的 action 都通过 moss 提供了.
        :param container:
        :param thread:
        :return:
        """
        compiler = container.force_fetch(MossCompiler)
        compiler.with_locals()
        moss_action = MossQuestAction(compiler, thread=thread)
        return [moss_action]
