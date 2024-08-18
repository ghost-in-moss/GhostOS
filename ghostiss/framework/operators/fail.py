from typing import Optional, List
from ghostiss.core.ghosts import Operator, Ghost
from ghostiss.core.messages import MessageKind
from ghostiss.core.session import DefaultEventType, TaskState


class FailOperator(Operator):
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
            reason: str,
            messages: List[MessageKind],
    ):
        self.reason = reason
        self.messages = messages

    def format_cancel_children_reason(self) -> str:
        if not self.reason:
            return ""
        return f"task is canceled cause parent task is failed: {self.reason}"

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
        task.state = TaskState.CANCELLED
        if self.reason:
            task.logs.append(f"{TaskState.FAILED}: {self.reason}")

        appending = thread.get_appending()
        if task.parent:
            # 发送消息给父任务.
            utils.send_task_event(
                task_id=task.parent,
                event_type=DefaultEventType.FAILURE_CALLBACK,
                messages=appending,
                self_task=task,
            )

        # 更新当前 session, 主要更新 thread 的状态.
        session.update_task(task, thread)

        # finish 没有后续. 但还是要执行一个反思事件.
        event = DefaultEventType.FAILED.new(
            task_id=task.task_id,
            messages=[],
        )

        # 立刻执行 on_finished 事件,
        return g.utils().handle_event(event)

    def destroy(self) -> None:
        del self.messages
