from typing import Tuple, Optional, Iterable
from abc import ABC, abstractmethod
from ghostiss.container import Container
from ghostiss.core.ghosts.operators import Operator, ActionOperator
from ghostiss.core.ghosts.actions import Action
from ghostiss.core.runtime.threads import Thread
from ghostiss.core.runtime.llms import LLMApi, Chat
from ghostiss.core.messages.messenger import Messenger

__all__ = [
    'Runner', 'LLMRunner', 'PipelineRunner',
]


class Runner(ABC):
    """
    必须要拆分一个抽象, 方便做单元测试和复用.
    通常用于 Thought 的内部.
    """

    @abstractmethod
    def run(self, container: Container, thread: Thread) -> Tuple[Thread, Optional[Operator]]:
        """
        运行 Thread, 同时返回一个新的 Thread. 不做存储修改, 方便单元测试.
        """
        pass


class LLMRunner(Runner, ABC):
    """
    标准的 Runner 设计.
    """

    @abstractmethod
    def prepare(self, container: Container, thread: Thread) -> Tuple[Iterable[Action], Chat]:
        """
        基于 thread 生成一个 chat 对象.
        """
        pass

    @abstractmethod
    def get_llmapi(self, container: Container) -> LLMApi:
        """
        获取 llmapi.
        """
        pass

    @abstractmethod
    def messenger(self, container: Container) -> Messenger:
        """
        返回流式传输所用的 messenger.
        """
        pass

    def run(self, container: Container, thread: Thread) -> Tuple[Thread, Optional[Operator]]:
        """
        标准的 llm runner 运行逻辑.
        """
        # 基于 thread 生成 chat 对象.
        # 获取当前运行依赖的 actions.
        actions, chat = self.prepare(container, thread)
        # 准备好回调的 map.
        actions_name_map = {}
        for action in actions:
            actions_name_map[action.name()] = action
        # 获取 llm 的 api.
        api = self.get_llmapi(container)
        messenger = self.messenger(container)
        api.deliver_chat_completion(chat, messenger)
        buffed = messenger.flush()
        thread.update(buffed.messages)

        for caller in buffed.callers:
            if caller.name not in actions_name_map:
                continue
            action = actions_name_map[caller.name]
            op = ActionOperator(action=action, arguments=caller.arguments)
            if op is not None:
                return thread, op
        return thread, None


class PipelineRunner(Runner):
    """
    管道式的 runner.
    """

    def __init__(self, pipes: Iterable[Runner]):
        self.pipes = pipes

    def run(self, container: Container, thread: Thread) -> Tuple[Thread, Optional[Operator]]:
        for pipe in self.pipes:
            # 任意一个 runner 返回 op, 会中断其它的 runner.
            thread, op = pipe.run(container, thread)
            if op is not None:
                return thread, op
        return thread, None
