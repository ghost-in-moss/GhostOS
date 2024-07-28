from typing import Iterable, Optional, Tuple, List, Dict
from ghostiss.container import Container
from ghostiss.core.ghosts import (
    Action, MOSSAction,
    LLMRunner,
    Operator,
)
from ghostiss.core.ghosts.messenger import Messenger
from ghostiss.core.moss import MOSS, PyContext
from ghostiss.core.messages import DefaultTypes
from ghostiss.core.runtime.llms import LLMs, LLMApi, Chat, ChatFilter, filter_chat
from ghostiss.core.runtime.threads import Thread, thread_to_chat
from ghostiss.helpers import uuid
from pydantic import BaseModel, Field
from ghostiss.framework.llms.chatfilters import AssistantNameFilter


class MossRunner(LLMRunner):
    """
    llm runner with moss
    """

    def __init__(
            self, *,
            name: str,
            system_prompt: str,
            instruction: str,
            llm_api_name: str = "",
            pycontext: Optional[PyContext] = None,
            **variables,
    ):
        self._name = name
        self._system_prompt = system_prompt
        self._instruction = instruction
        self._llm_api_name = llm_api_name
        self._pycontext = pycontext
        self._variables = variables

    def actions(self, container: Container, thread: Thread) -> Iterable[Action]:
        moss = container.force_fetch(MOSS)
        if self._variables:
            moss = moss.with_vars(**self._variables)
        if self._pycontext:
            moss.update_context(self._pycontext)
        moss = moss.update_context(thread.pycontext)
        yield MOSSAction(moss, thread=thread)

    def prepare(self, container: Container, thread: Thread) -> Tuple[Iterable[Action], Chat]:
        """
        生成默认的 chat.
        :param container:
        :param thread:
        :return:
        """
        system = [
            DefaultTypes.DEFAULT.new_system(content=self._system_prompt),
            DefaultTypes.DEFAULT.new_system(content=self._instruction),
        ]
        chat = thread_to_chat(chat_id=uuid(), thread=thread, system=system)
        actions = self.actions(container, thread)
        result_actions = []
        for action in actions:
            chat = action.update_chat(chat)
            result_actions.append(action)
        # 进行一些消息级别的加工.
        filters = self.filters()
        chat = filter_chat(chat, filters)
        return result_actions, chat

    def filters(self) -> Iterable[ChatFilter]:
        yield AssistantNameFilter(name=self._name)

    def get_llmapi(self, container: Container) -> LLMApi:
        llms = container.force_fetch(LLMs)
        return llms.get_api(self._llm_api_name)


class MOSSRunnerTestSuite(BaseModel):
    """
    模拟一个 MOSSRunner 的单元测试.
    """
    agent_name: str = Field(default="")

    system_prompt: str = Field(
        description="定义系统 prompt. "
    )
    instruction: str = Field(
        description="定义当前 Runner 的 prompt",
    )
    llm_apis: List = Field(
        description="定义当前 runner 运行时使用的 llm api 是哪一个. ",
    )
    pycontext: PyContext = Field(
        description="定义 pycontext. "
    )
    thread: Thread = Field(
        description="定义一个上下文. "
    )

    def get_runner(self, llm_api: str) -> MossRunner:
        """
        从配置文件里生成 runner 的实例.
        """
        return MossRunner(
            name=self.agent_name,
            system_prompt=self.system_prompt,
            instruction=self.instruction,
            llm_api_name=llm_api,
            pycontext=self.pycontext,
        )

    def run_test(self, container: Container) -> Dict[str, Tuple[Thread, Chat, Optional[Operator]]]:
        """
        基于 runner 实例运行测试. 如何渲染交给外部实现.
        """
        from threading import Thread
        parallels = []
        outputs = {}

        def run(_api: str, _runner: MossRunner, _messenger: Messenger, _thread: Thread):
            """
            定义一个闭包.
            """
            _, _chat = _runner.prepare(container, _thread)
            _llm_api = _runner.get_llmapi(container)
            _chat = _llm_api.parse_chat(_chat)
            _op = _runner.run(container, _messenger, _thread)
            outputs[_api] = (_thread, _chat, _op)

        for llm_api in self.llm_apis:
            t = Thread(
                target=run,
                args=(
                    llm_api, self.get_runner(llm_api), container.force_fetch(Messenger), self.thread.thread_copy()
                ),
            )
            t.start()
            parallels.append(t)

        for t in parallels:
            t.join()
        return outputs
