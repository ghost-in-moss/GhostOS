from typing import Optional, List

from ghostiss.core.ghosts import (
    Operator, Ghost,
)
from ghostiss.core.messages import (
    MessageKind,
)
from ghostiss.core.session import (
    DefaultEventType,
    TaskState,
)


class ObserveOperator(Operator):
    """
    运行下一轮思考.
    """

    def __init__(
            self, *,
            observation: List[MessageKind],
            log: str = "",
            caller_id: str = "",
    ):
        self.observation = observation
        self.log = log
        self.caller_id = caller_id

    def run(self, g: "Ghost") -> Optional["Operator"]:
        session = g.session()
        if self.observation:
            session.send_messages(*self.observation)

        task = session.task()
        thread = session.thread()
        appending = thread.get_appending()
        task.state = TaskState.RUNNING
        if self.log:
            task.logs.append(f"{TaskState.RUNNING}: {self.log}")
        # 必须要有消息时才发送.
        if appending and task.parent:
            utils = g.utils()
            utils.send_task_event(
                task_id=task.parent,
                event_type=DefaultEventType.NOTIFY_CALLBACK.value,
                messages=appending,
                self_task=task,
            )
        session.update_task(task, thread)
        # 执行下一轮思考.
        utils = g.utils()
        utils.send_task_event(
            task_id=task.task_id,
            event_type=DefaultEventType.THINK.value,
            messages=[],
            self_task=task,
        )
        return None

    def destroy(self) -> None:
        del self.observation
