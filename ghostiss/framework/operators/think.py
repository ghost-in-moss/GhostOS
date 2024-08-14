from typing import Optional, List

from ghostiss.core.ghosts import (
    Operator, Ghost,
)
from ghostiss.core.messages import (
    MessageType,
)
from ghostiss.core.session import (
    DefaultEventType,
    TaskState,
)


class ThinkAnotherRoundOperator(Operator):
    """
    运行下一轮思考.
    """

    def __init__(
            self, *,
            observation: List[MessageType],
            log: str = "",
    ):
        self.observation = observation
        self.log = log

    def run(self, g: "Ghost") -> Optional["Operator"]:
        session = g.session()
        if self.observation:
            session.send_messages(*self.observation)

        task = session.task()
        thread = session.thread()
        appending = thread.get_appending(ignore_delivered=True)
        task.state = TaskState.RUNNING
        if self.log:
            task.logs.append(f"{TaskState.RUNNING}: {self.log}")
        if appending and task.parent:
            utils = g.utils()
            utils.send_task_event(
                task_id=task.parent,
                event_type=DefaultEventType.NOTIFY_CALLBACK.value,
                messages=appending,
                self_task=task,
            )
        session.update_task(task, thread)
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
