from typing import Optional
from abc import ABC, abstractmethod
from ghostiss.entity import Entity, EntityFactory, EntityMeta
from ghostiss.core.ghosts.ghost import Ghost
from ghostiss.core.ghosts.events import Event
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.runner import Runner
from ghostiss.core.abc import Identifiable, Descriptive
from ghostiss.helpers import uuid


class Thought(Entity, Identifiable, Descriptive, ABC):
    """
    思维状态机的驱动.
    """

    def get_description(self) -> str:
        return self.identifier().get_description()

    @abstractmethod
    def new_task_id(self, g: Ghost) -> str:
        """
        创建一个唯一的 task id.
        """
        pass

    def on_event(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        接受 event 并作出响应.
        """
        name = e.type
        method = "on_" + name
        if hasattr(self, method):
            return getattr(self, method)(g, e)
        return None


class BasicThought(Thought, ABC):

    def new_task_id(self, g: Ghost) -> str:
        # 如果生成的 task id 是不变的, 则在同一个 process 里是一个单例. 但要考虑互相污染的问题.
        return uuid()

    def on_create(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        基于 Thought 创建一个 Task 时触发的事件.
        可以根据事件做必要的初始化.
        """
        #  默认没有任何动作.
        return None

    def on_finished(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        当前 Thought 所生成的 task 结束之后, 会回调的事件.
        """
        # 默认没有任何动作.
        return None

    def on_input(self, g: Ghost, e: Event) -> Optional[Operator]:
        """
        接受到一个外部事件后执行的逻辑.
        """
        return self._run_event(g, e)

    @abstractmethod
    def runner(self, g: Ghost, e: Event) -> Runner:
        pass

    def _run_event(self, g: Ghost, e: Event) -> Optional[Operator]:
        runner = self.runner(g, e)
        session = g.session
        thread = session.thread()
        # thread 更新消息体.
        thread.inputs = e.messages
        messenger = g.messenger()
        # 执行 runner.
        op = runner.run(g.container, messenger, thread)
        return op

    def on_finish_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        session = g.session
        task = session.task()
        awaiting = task.awaiting_tasks()
        if e.from_task_id not in awaiting:
            # todo: log
            return None
        # 添加消息.
        messenger = g.messenger()
        thread = session.thread()
        thread.inputs = e.messages

        fulfilled = task.update_awaits(e.from_task_id)
        session.update_task(task)

        op = None
        if fulfilled:
            runner = self.runner(g, e)
            thread, op = runner.run(g.container, messenger, thread)
        session.update_thread(thread)
        return op

    def on_failure_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        return self._run_event(g, e)

    def on_wait_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        return self._run_event(g, e)


class Thoughts(EntityFactory[Thought], ABC):
    """
    管理所有的 Thoughts.
    """

    @abstractmethod
    def new_entity(self, meta_data: EntityMeta) -> Optional[Thought]:
        pass

    @abstractmethod
    def register(self, thought: Thought) -> None:
        """
        注册一个 Thought 实例到当前的 Thoughts.
        """
        pass

    @abstractmethod
    def get_thought(self, thought_id: str) -> Optional[Thought]:
        pass

    @abstractmethod
    def force_get_thoughts(self, thought_id: str) -> Optional[Thought]:
        pass

    def new_thought(self, meta: EntityMeta) -> Thought:
        return self.force_new_entity(meta)
