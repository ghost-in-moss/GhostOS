from typing import List, Optional, Tuple
from abc import ABC, abstractmethod
from ghostiss.entity import Entity, EntityFactory, EntityMeta, ENTITY_TYPE
from ghostiss.core.ghosts.ghost import Ghost
from ghostiss.core.ghosts.events import Event
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.runtime.threads import Thread
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
        # 可以控制单例.
        return uuid()

    def on_create(self, g: Ghost, e: Event) -> Optional[Operator]:
        #  默认没有任何动作.
        return None

    def on_finish(self, g: Ghost, e: Event) -> Optional[Operator]:
        # 默认没有任何动作.
        return None

    def on_input(self, g: Ghost, e: Event) -> Optional[Operator]:
        return self._run_event(g, e)

    def _run_event(self, g: Ghost, e: Event) -> Optional[Operator]:
        session = g.session
        thread = session.thread()
        # thread 更新消息体.
        thread.update(e.messages)
        thread, op = self.idea(g, e).run(thread)
        # runtime 更新消息.
        session.update_thread(thread)
        return op

    def on_finish_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        session = g.session
        task = session.task()
        awaiting = task.awaiting_tasks()
        if e.from_task_id not in awaiting:
            # todo: log
            return None
        # 添加消息.
        thread = session.thread()
        thread.update(e.messages)

        fulfilled = task.update_awaits(e.from_task_id)
        session.update_task(task)

        op = None
        if fulfilled:
            thread, op = self.idea(g, e).run(thread)
        session.update_thread(thread)
        return op

    def on_failure_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        return self._run_event(g, e)

    def on_wait_callback(self, g: Ghost, e: Event) -> Optional[Operator]:
        return self._run_event(g, e)


class Thoughts(EntityFactory[Thought], ABC):

    def new_entity(self, meta_data: EntityMeta) -> Optional[Thought]:
        pass

    def find_thought(self, meta: EntityMeta) -> Thought:
        return self.force_new_entity(meta)
