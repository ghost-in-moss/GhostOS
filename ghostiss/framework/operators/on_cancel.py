from typing import Optional, List
from ghostiss.core.ghosts import (
    EventOperator, Ghost, Operator,
)
from ghostiss.core.session import (
    DefaultEventType,
    TaskState, Event,
)


class OnCancelOperator(EventOperator):
    """
    任务接收到 cancel 事件.
    通常来自父任务. cancel 事件有绝对的权威.
    """

    event_type = DefaultEventType.CANCELED

    def __init__(self, event: Event):
        self.event = event

    @classmethod
    def new(cls, event: Event) -> "EventOperator":
        return cls(event)

    def run(self, g: "Ghost") -> Optional["Operator"]:
        session = g.session()
        task = session.task()
        # 变更当前状态.
        if task.state != TaskState.CANCELLED:
            task.task_state = TaskState.CANCELLED
        # 取消自己的所有子任务.
        utils = g.utils()
        utils.cancel_children_tasks(
            reason=f"parent task {task.task_id} is cancelled",
            self_task=task,
        )
        session.update_task(task)
        # 执行事件:
        return utils.handle_event(self.event)

    def destroy(self) -> None:
        del self.event
