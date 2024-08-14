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


class FinishOperator(Operator):
    """
    结束当前任务.
    1. 通过 session 发送消息, 同时消息保存到 Thread 里.
    2. 变更当前 Task 的状态, 并保存.
    3. 反馈 finish_callback 事件给父 task, 如果存在的话.
    4. 取消未完成的子任务. 向它们发送取消事件.
    5. 自己继续执行 on_finished 事件, 可以创建独立的任务去理解.
    """

    def __init__(
            self, *,
            log: str,
            messages: List[MessageType],
            reason_formatter: str = "task is canceled cause parent task is finished: {log}"
    ):
        self.log = log
        self.messages = messages
        self.reason_formatter = reason_formatter

    def format_cancel_children_reason(self) -> str:
        if not self.log:
            return ""
        return f"task is canceled cause parent task is finished: {self.log}"

    def run(self, g: "Ghost") -> Optional["Operator"]:
        utils = g.utils()
        session = g.session()
        if self.messages:
            session.send_messages(*self.messages)
        # 取消所有的子任务.
        reason = self.format_cancel_children_reason()
        utils.cancel_children_tasks(reason=reason, includes=None)

        # 更新当前任务状态.
        task = session.task()
        # 状态判断.
        thread = session.thread()
        # 变更当前任务的状态.
        task.state = TaskState.FINISHED
        if self.log:
            task.logs.append(f"{TaskState.FINISHED}: {self.log}")

        if task.parent:
            # 发送消息给父任务.
            utils.send_task_event(
                task_id=task.parent,
                event_type=DefaultEventType.FINISH_CALLBACK,
                messages=thread.get_appending(ignore_delivered=True),
                self_task=task,
            )

        # 更新当前 session, 主要更新 thread 的状态.
        session.update_task(task, thread)

        # finish 没有后续. 但还是要执行一个反思事件.
        event = DefaultEventType.FINISHED.new(
            task_id=task.task_id,
            messages=[],
        )

        # 立刻执行 on_finished 事件,
        return g.utils().handle_event(event)

    def destroy(self) -> None:
        del self.messages
