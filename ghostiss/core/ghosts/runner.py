from typing import Tuple, Optional, Iterable
from abc import ABC, abstractmethod
from ghostiss.container import Container
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.actions import Action
from ghostiss.core.session.threads import MsgThread
from ghostiss.core.llms import LLMApi, Chat
from ghostiss.core.session import Session
from ghostiss.core.session.messenger import Messenger

__all__ = [
    'Runner', 'LLMRunner', 'PipelineRunner',
]


class Runner(ABC):
    """
    原本大模型思维状态机的设计就是 Thought.
    这里必须要从 Thought 内部拆分一个抽象, 目的是方便做单元测试和复用.
    """

    @abstractmethod
    def run(self, container: Container, messenger: Messenger, thread: MsgThread) -> Optional[Operator]:
        """
        运行 Thread, 同时返回一个新的 Thread. 不做存储修改, 方便单元测试.
        """
        pass


class NewRunner(ABC):
    """
    准备取代 runner, 先做一个独立的然后再改名.
    """

    @abstractmethod
    def run(self, container: Container, session: Session) -> Optional[Operator]:
        pass


class LLMRunner(Runner, ABC):
    """
    标准的 Runner 设计, 使用大模型来驱动运行逻辑.
    是否还会有其它的 Runner 呢?
    举两个简单的例子:
    1. 如果多个 Runner 需要并发运行, 则可以将多个 Runner 包装到一个 ParallelRunner
    2. 如果多个 Runner 在一次运行中要串行执行, 任何 Runner 返回 op 后中断. 可以将多个 Runner 包装到一个 PipelineRunner.
    """

    @abstractmethod
    def prepare(self, container: Container, thread: MsgThread) -> Tuple[Iterable[Action], Chat]:
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

    def run(self, container: Container, messenger: Messenger, thread: MsgThread) -> Optional[Operator]:
        """
        标准的 llm runner 运行逻辑.
        """
        # 基于 thread 生成 chat 对象.
        # 获取当前运行依赖的 actions.
        actions, chat = self.prepare(container, thread)
        # 准备好回调的 map.
        actions_name_map = {}
        for action in actions:
            name = action.identifier().name
            actions_name_map[name] = action
        # 获取 llm 的 api.
        api = self.get_llmapi(container)
        # todo: with payload
        deliver = messenger.new(thread=thread, functional_tokens=chat.functional_tokens)
        api.deliver_chat_completion(chat, deliver)
        messages, callers = deliver.flush()
        for caller in callers:
            if caller.name not in actions_name_map:
                continue
            action = actions_name_map[caller.name]
            # todo: with payload
            deliver = messenger.new(thread=thread)
            op = action.act(container, deliver, caller)
            deliver.flush()
            if op is not None:
                return op
        return None


class PipelineRunner(Runner):
    """
    管道式的 runner. 做一个示范.
    """

    def __init__(self, pipes: Iterable[Runner]):
        self.pipes = pipes

    def run(self, container: Container, messenger: Messenger, thread: MsgThread) -> Optional[Operator]:
        for pipe in self.pipes:
            # 任意一个 runner 返回 op, 会中断其它的 runner.
            thread, op = pipe.run(container, messenger, thread)
            if op is not None:
                return op
        return None
