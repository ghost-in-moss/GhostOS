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


class AwaitsOperator(Operator):
    """
    当前任务进入等待状态. 需要执行的流程:
    1. 发送存在的消息.
    2. 更新当前 task 的状态, 添加日志.
    3. 如果父任务存在, 向父任务发送消息.
    """

    def __init__(
            self, *,
            replies: List[MessageType],
            log: str = "",
    ):
        self.log = log
        self.replies = replies

    def run(self, g: "Ghost") -> Optional["Operator"]:
        utils = g.utils()
        session = g.session()
        if self.replies:
            session.send_messages(*self.replies)
        # 变更当前任务的状态.
        # 更新当前任务状态.
        task = session.task()
        task.state = TaskState.WAITING
        if self.log:
            task.logs.append(f"{TaskState.WAITING}: {self.log}")

        # 状态判断.
        thread = session.thread()
        appending = thread.get_appending(ignore_delivered=True)
        # 消息不为空的时候才发送.
        if appending and task.parent:
            # 发送消息给父任务.
            utils.send_task_event(
                task_id=task.parent,
                event_type=DefaultEventType.WAIT_CALLBACK,
                messages=appending,
                self_task=task,
            )

        # 更新当前 session, 主要更新 thread 的状态.
        session.update_task(task, thread)
        return None

    def destroy(self) -> None:
        del self.replies
