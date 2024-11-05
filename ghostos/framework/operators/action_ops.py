from typing import Optional, List, ClassVar

from ghostos.core.ghosts import (
    Operator, Ghost, NewTask,
)
from ghostos.core.messages import (
    MessageKind, MessageKindParser, Role,
)
from ghostos.core.session import (
    EventTypes,
    TaskState,
    GoTaskStruct,
)

__all__ = [
    'ActionOperator',
    'WaitsOperator',
    'FailOperator',
    'FinishOperator',
    'ThinkOperator',
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
    callback_event_type: ClassVar[str] = EventTypes.WAIT_CALLBACK.value

    def __init__(
            self, *,
            messages: List[MessageKind],
            reason: str = "",
            instruction: str = "",
            callback_task_id: Optional[str] = None,
    ):
        self.reason = reason
        self.instruction = instruction
        self.messages = messages
        self.callback_task_id = callback_task_id

    def send_replies(self, g: "Ghost") -> None:
        if self.messages:
            session = g.session()
            self.messages = session.send_messages(*self.messages)

    def get_callback_task_id(self, task: GoTaskStruct) -> Optional[str]:
        if self.callback_task_id is not None:
            return self.callback_task_id
        return task.parent

    def change_task_state(self, g: "Ghost") -> None:
        session = g.session()
        task = session.task()
        thread = session.thread()
        task.state = self.task_state
        if self.reason:
            task.logs.append(f"{self.task_state}: {self.reason}")
        # 状态判断.
        # 消息不为空的时候才发送.
        callbacks = self.messages
        callback_task_id = self.get_callback_task_id(task)
        if callback_task_id:
            utils = g.utils()
            # 发送消息给父任务.
            utils.send_task_event(
                task_id=callback_task_id,
                event_type=self.callback_event_type,
                messages=callbacks,
                reason=self.reason,
                self_task=task,
            )

        # 更新当前 session, 主要更新 thread 的状态.
        session.update_task(task, thread, True)

    def send_children_events(self, g: "Ghost") -> None:
        return

    def next_operator(self, g: "Ghost") -> Optional[Operator]:
        return None

    def run(self, g: "Ghost") -> Optional["Operator"]:
        self.send_replies(g)
        self.send_children_events(g)
        self.change_task_state(g)
        self.send_children_events(g)
        return self.next_operator(g)

    def destroy(self) -> None:
        del self.messages


class WaitsOperator(ActionOperator):
    task_state: ClassVar[str] = TaskState.WAITING.value
    callback_event_type: ClassVar[str] = EventTypes.WAIT_CALLBACK.value

    def __init__(self, *, reason: str, messages: List[MessageKind], callback_task_id: Optional[str] = None):
        super().__init__(reason=reason, messages=messages, callback_task_id=callback_task_id)


class FailOperator(ActionOperator):
    """
    结束当前任务.
    1. 通过 session 发送消息, 同时消息保存到 Thread 里.
    2. 变更当前 Task 的状态, 并保存.
    3. 反馈 fail_callback 事件给父 task, 如果存在的话.
    4. 取消未完成的子任务. 向它们发送取消事件.
    5. 自己继续执行 on_finished 事件, 可以创建独立的任务去理解.
    """
    task_state: ClassVar[str] = TaskState.FAILED.value
    callback_event_type: ClassVar[str] = EventTypes.FAILURE_CALLBACK.value

    def __init__(
            self, *,
            reason: str,
            messages: List[MessageKind],
            callback_task_id: Optional[str] = None,
    ):
        super().__init__(reason=reason, messages=messages, callback_task_id=callback_task_id)

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
        event = EventTypes.FAILED.new(
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
    callback_event_type: ClassVar[str] = EventTypes.FINISH_CALLBACK.value

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
        event = EventTypes.FINISHED.new(
            task_id=task.task_id,
            messages=[],
        )

        # 立刻执行 on_finished 事件,
        return g.utils().handle_event(event)


class WaitOnTasksOperator(ActionOperator):
    """
    wait on children tasks
    """
    task_state: ClassVar[str] = TaskState.RUNNING.value
    callback_event_type: ClassVar[str] = EventTypes.NOTIFY.value

    def __init__(
            self, *,
            new_tasks: List[NewTask],
    ):
        for item in new_tasks:
            if not isinstance(item, NewTask):
                raise TypeError(f'new_tasks must be a NewTask instance, got {type(item)}')
        self.new_tasks = new_tasks
        super().__init__(
            messages=[],
            reason="",
            instruction="",
        )

    def send_children_events(self, g: "Ghost") -> None:
        g.utils().create_child_tasks(
            depend=True,
            new_tasks=self.new_tasks,
        )

    def destroy(self) -> None:
        del self.new_tasks
        del self.messages


class ThinkOperator(ActionOperator):
    """
    运行下一轮思考.
    """
    task_state: ClassVar[str] = TaskState.RUNNING.value
    callback_event_type: ClassVar[str] = EventTypes.NOTIFY.value

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
            event_type=EventTypes.ROTATE.value,
            reason=self.reason,
            instruction=self.instruction,
            messages=observations,
            self_task=task,
        )
        return None

    def destroy(self) -> None:
        del self.observation
