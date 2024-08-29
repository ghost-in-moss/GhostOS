from typing import Optional, List, ClassVar

from ghostos.core.ghosts import (
    Operator, Ghost, Thought,
)
from ghostos.core.messages import (
    MessageKind, MessageKindParser, Role,
)
from ghostos.core.session import (
    DefaultEventType,
    TaskState,
)

__all__ = [
    'ActionOperator',
    'WaitsOperator',
    'FailOperator',
    'FinishOperator',
    'ObserveOperator',
    'WaitOnTasksOperator',
]


class ActionOperator(Operator):
    """
    当前任务进入等待状态. 需要执行的流程:
    1. 发送存在的消息.
    2. 更新当前 task 的状态, 添加日志.
    3. 如果父任务存在, 向父任务发送消息.
    """
    task_state: ClassVar[str] = TaskState.WAITING.value
    callback_event_type: ClassVar[str] = DefaultEventType.WAIT_CALLBACK

    def __init__(
            self, *,
            messages: List[MessageKind],
            reason: str = "",
            instruction: str = "",
    ):
        self.reason = reason
        self.instruction = instruction
        self.messages = messages

    def send_replies(self, g: "Ghost") -> None:
        session = g.session()
        if self.messages:
            session.send_messages(*self.messages)

    def change_task_state(self, g: "Ghost") -> None:
        session = g.session()
        task = session.task()
        task.state = self.task_state
        if self.reason:
            task.logs.append(f"{self.task_state}: {self.reason}")
        # 状态判断.
        thread = session.thread()
        generates = thread.get_generates()
        # 消息不为空的时候才发送.
        if generates and task.parent:
            callbacks = []
            for message in generates:
                if message.get_content().strip():
                    callbacks.append(message)
            if callbacks:
                utils = g.utils()
                # 发送消息给父任务.
                utils.send_task_event(
                    task_id=task.parent,
                    event_type=self.callback_event_type,
                    messages=generates,
                    reason=self.reason,
                    self_task=task,
                )

        # 更新当前 session, 主要更新 thread 的状态.
        session.update_task(task, thread, True)

    def send_children_events(self, g: "Ghost") -> None:
        pass

    def next_operator(self, g: "Ghost") -> Optional[Operator]:
        return None

    def run(self, g: "Ghost") -> Optional["Operator"]:
        self.send_children_events(g)
        self.change_task_state(g)
        self.send_children_events(g)
        return self.next_operator(g)

    def destroy(self) -> None:
        del self.messages


class WaitsOperator(ActionOperator):
    task_state: ClassVar[str] = TaskState.WAITING.value
    callback_event_type: ClassVar[str] = DefaultEventType.WAIT_CALLBACK

    def __init__(self, *, reason: str, messages: List[MessageKind]):
        super().__init__(reason=reason, messages=messages)


class FailOperator(ActionOperator):
    """
    结束当前任务.
    1. 通过 session 发送消息, 同时消息保存到 Thread 里.
    2. 变更当前 Task 的状态, 并保存.
    3. 反馈 finish_callback 事件给父 task, 如果存在的话.
    4. 取消未完成的子任务. 向它们发送取消事件.
    5. 自己继续执行 on_finished 事件, 可以创建独立的任务去理解.
    """
    task_state: ClassVar[str] = TaskState.FAILED.value
    callback_event_type: ClassVar[str] = DefaultEventType.FAILURE_CALLBACK

    def __init__(
            self, *,
            reason: str,
            messages: List[MessageKind],
    ):
        super().__init__(reason=reason, messages=messages)

    def format_cancel_children_reason(self) -> str:
        if not self.reason:
            return ""
        return f"task is canceled cause parent task is failed: {self.reason}"

    def send_children_events(self, g: "Ghost") -> None:
        # 取消所有的子任务.
        reason = self.format_cancel_children_reason()
        utils = g.utils()
        utils.cancel_children_tasks(reason=reason, includes=None)

    def next_operator(self, g: "Ghost") -> Optional[Operator]:
        session = g.session()
        task = session.task()
        # finish 没有后续. 但还是要执行一个反思事件.
        event = DefaultEventType.FAILED.new(
            task_id=task.task_id,
            messages=[],
        )
        # 立刻执行 on_finished 事件,
        return g.utils().handle_event(event)


class FinishOperator(ActionOperator):
    """
    结束当前任务.
    1. 通过 session 发送消息, 同时消息保存到 Thread 里.
    2. 变更当前 Task 的状态, 并保存.
    3. 反馈 finish_callback 事件给父 task, 如果存在的话.
    4. 取消未完成的子任务. 向它们发送取消事件.
    5. 自己继续执行 on_finished 事件, 可以创建独立的任务去理解.
    """
    task_state: ClassVar[str] = TaskState.FINISHED.value
    callback_event_type: ClassVar[str] = DefaultEventType.FINISH_CALLBACK

    def __init__(
            self, *,
            reason: str,
            messages: List[MessageKind],
    ):
        super().__init__(
            messages=messages,
            reason=reason,
        )

    def format_cancel_children_reason(self) -> str:
        if not self.reason:
            return ""
        return f"task is canceled cause parent task is finished: {self.reason}"

    def send_children_events(self, g: "Ghost") -> None:
        utils = g.utils()
        reason = self.format_cancel_children_reason()
        utils.cancel_children_tasks(reason=reason, includes=None)

    def next_operator(self, g: "Ghost") -> Optional[Operator]:
        # finish 没有后续. 但还是要执行一个反思事件.
        session = g.session()
        task = session.task()
        event = DefaultEventType.FINISHED.new(
            task_id=task.task_id,
            messages=[],
        )

        # 立刻执行 on_finished 事件,
        return g.utils().handle_event(event)


class WaitOnTasksOperator(ActionOperator):
    task_state: ClassVar[str] = TaskState.RUNNING.value
    callback_event_type: ClassVar[str] = DefaultEventType.NOTIFY_CALLBACK

    def __init__(
            self, *,
            thoughts: List[Thought],
            reason: str = "",
            instruction: str = "",
    ):
        self.thoughts = thoughts
        super().__init__(
            messages=[],
            reason=reason,
            instruction=instruction,
        )

    def send_children_events(self, g: "Ghost") -> None:
        g.utils().create_child_tasks(
            depend=True,
            thoughts=list(self.thoughts),
            reason=self.reason,
            instruction=self.instruction,
        )

    def destroy(self) -> None:
        del self.thoughts
        del self.messages


class ObserveOperator(ActionOperator):
    """
    运行下一轮思考.
    """
    task_state: ClassVar[str] = TaskState.RUNNING.value
    callback_event_type: ClassVar[str] = DefaultEventType.NOTIFY_CALLBACK

    def __init__(
            self, *,
            reason: str,
            instruction: str,
            observation: List[MessageKind],
            caller_id: str = "",
    ):
        self.observation = observation
        self.caller_id = caller_id
        super().__init__(
            messages=[],
            reason=reason,
            instruction=instruction,
        )

    def next_operator(self, g: "Ghost") -> Optional["Operator"]:
        observations = []
        if self.observation:
            parser = MessageKindParser(role=Role.TOOL, ref_id=self.caller_id)
            observations = parser.parse(self.observation)
        task = g.session().task()
        # 执行下一轮思考.
        utils = g.utils()
        utils.send_task_event(
            task_id=task.task_id,
            event_type=DefaultEventType.OBSERVE.value,
            reason=self.reason,
            instruction=self.instruction,
            messages=observations,
            self_task=task,
        )
        return None

    def destroy(self) -> None:
        del self.observation
