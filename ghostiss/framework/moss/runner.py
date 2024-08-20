from typing import Iterable, Optional, Tuple, List, Dict
from ghostiss.container import Container
from ghostiss.core.ghosts import (
    Action,
    LLMRunner,
    Operator,
)
import datetime
from ghostiss.core.session.messenger import Messenger
from ghostiss.core.moss_p1 import MOSS, PyContext
from ghostiss.core.messages import DefaultMessageTypes, Message
from ghostiss.core.llms import LLMs, LLMApi, Chat, ChatUpdater, update_chat
from ghostiss.core.session.threads import MsgThread, thread_to_chat
from ghostiss.helpers import uuid, import_from_path
from pydantic import BaseModel, Field
from ghostiss.framework.chatfilters.assistant_filter import OtherAgentOrTaskUpdater
from ghostiss.framework.moss.action import MOSSAction

__all__ = [
    'MossRunner',
    'MOSSRunnerTestResult', 'MOSSRunnerTestSuite',
]


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
            actions: Optional[List[Action]] = None,
            **variables,
    ):
        self._name = name
        self._system_prompt = system_prompt
        self._instruction = instruction
        self._llm_api_name = llm_api_name
        self._pycontext = pycontext
        self._variables = variables
        self._actions = actions

    def actions(self, container: Container, thread: MsgThread) -> Iterable[Action]:
        moss = container.force_fetch(MOSS)
        if self._variables:
            moss = moss.with_vars(**self._variables)
        if self._pycontext:
            moss = moss.update_context(self._pycontext)
        thread_pycontext = thread.get_pycontext()
        moss = moss.update_context(thread_pycontext)
        yield MOSSAction(moss, thread=thread)
        # 也遍历上层传入的 actions.
        if self._actions:
            for action in self._actions:
                yield action

    def prepare(self, container: Container, thread: MsgThread) -> Tuple[Iterable[Action], Chat]:
        """
        生成默认的 chat.
        :param container:
        :param thread:
        :return:
        """
        system = [
            DefaultMessageTypes.DEFAULT.new_system(content=self._system_prompt),
            DefaultMessageTypes.DEFAULT.new_system(content=self._instruction),
        ]
        chat = thread_to_chat(chat_id=uuid(), thread=thread, system=system)
        actions = self.actions(container, thread)
        result_actions = []
        for action in actions:
            chat = action.update_chat(chat)
            result_actions.append(action)
        # 进行一些消息级别的加工.
        filters = self.filters()
        chat = update_chat(chat, filters)
        return result_actions, chat

    def filters(self) -> Iterable[ChatUpdater]:
        yield OtherAgentOrTaskUpdater(assistant_name=self._name)

    def get_llmapi(self, container: Container) -> LLMApi:
        llms = container.force_fetch(LLMs)
        return llms.get_api(self._llm_api_name)


class MOSSRunnerTestResult(BaseModel):
    time: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    results: Dict[str, List[Message]] = Field(default_factory=dict)


class MOSSRunnerTestSuite(BaseModel):
    """
    模拟一个 MOSSRunner 的单元测试.
    """
    import_runner: Optional[str] = Field(
        default=None,
        description="runner 不是用 test suite 生成, 而是从目标路径 import 一个实例. "
    )

    last_round: Optional[str] = Field(
        default=None,
        description="relative file path of last round. if given, will join last round thread to current thread",
    )
    round_api: Optional[str] = Field(
        default=None,
        description="certain llm api name that used to generate new round messages. "
                    "if not given, use first one of llm_apis",
    )

    agent_name: str = Field(default="moss")

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
    thread: MsgThread = Field(
        description="定义一个上下文. "
    )
    actions: List[str] = Field(
        default_factory=list,
        description="use module:spec pattern to import action instances. such as foo.bar:zoo",
    )
    results: List[MOSSRunnerTestResult] = Field(
        default_factory=list,
        description="用来记录历史上测试的结果",
    )

    def get_runner(self, llm_api: str) -> MossRunner:
        """
        从配置文件里生成 runner 的实例.
        """
        if self.import_runner:
            runner: MossRunner = import_from_path(self.import_runner)
            if not isinstance(runner, MossRunner):
                raise AttributeError(f"import {self.import_runner} must be an instance of MossRunner")
            runner._llm_api_name = llm_api
            # 跳过其它配置项.
            return runner

        actions = []
        if self.actions:
            for action in self.actions:
                imported = import_from_path(action)
                if not isinstance(imported, Action):
                    raise AttributeError(f"{imported} imported from {action} is not an action")
                actions.append(imported)

        return MossRunner(
            name=self.agent_name,
            system_prompt=self.system_prompt,
            instruction=self.instruction,
            llm_api_name=llm_api,
            actions=actions,
            pycontext=self.pycontext,
        )

    def run_test(
            self,
            container: Container,
            thread: Optional[MsgThread] = None,
    ) -> Dict[str, Tuple[MsgThread, Chat, Optional[Operator]]]:
        """
        基于 runner 实例运行测试. 如何渲染交给外部实现.
        """
        from threading import Thread as OSThread
        parallels = []
        outputs = {}
        thread = thread if thread else self.thread

        def run(_api: str, _runner: MossRunner, _messenger: Messenger, _thread: MsgThread):
            """
            定义一个闭包.
            """
            _, _chat = _runner.prepare(container, _thread)
            _messenger = _messenger.new()
            _llm_api = _runner.get_llmapi(container)
            _chat = _llm_api.parse_chat(_chat)
            _op = _runner.run(container, _messenger, _thread)
            outputs[_api] = (_thread, _chat, _op)

        for llm_api in self.llm_apis:
            t = OSThread(
                target=run,
                args=(
                    llm_api, self.get_runner(llm_api), container.force_fetch(Messenger), thread.thread_copy(),
                ),
            )
            t.start()
            parallels.append(t)

        for t in parallels:
            t.join()
        return outputs
