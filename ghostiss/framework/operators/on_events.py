from typing import Optional, ClassVar

from ghostiss.core.ghosts import (
    EventOperator, Ghost, Operator, get_event_operator
)
from ghostiss.core.session import (
    TaskState,
    DefaultEventType,
)

__all__ = [
    'OnEventOperator',

    # 上游相关事件.
    'OnUpstreamEventOperator',
    'OnInputOperator',
    'OnCancelOperator',
    'OnCreatedOperator',

    # 自身的事件.
    'OnSelfEventOperator',
    'OnThinkOperator',

    # 下游的 callback 事件.
    'OnCallbackEventOperator',
    'OnFinishCallbackOperator',
    'OnNotifyCallbackOperator',
    'OnWaitCallbackOperator',
    'OnFailureCallbackOperator',
]


class OnEventOperator(EventOperator):
    """
    标准的事件状态机. 区分上游事件, 自身事件, 和下游 callback 事件.
    """
    event_type: ClassVar[str] = ""

    def run(self, g: "Ghost") -> Optional["Operator"]:
        task = g.session().task()
        if self.event.from_self():
            op = get_event_operator(
                {
                    "": OnSelfEventOperator,
                    OnThinkOperator.event_type: OnThinkOperator,
                },
                self.event,
            )
            return op
        elif self.event.callback or self.event.from_task_id in task.children:
            op = get_event_operator(
                {
                    "": OnCallbackEventOperator,
                    OnFinishCallbackOperator.event_type: OnFinishCallbackOperator,
                    OnFailureCallbackOperator.event_type: OnFailureCallbackOperator,
                    OnWaitCallbackOperator.event_type: OnWaitCallbackOperator,
                    OnNotifyCallbackOperator.event_type: OnNotifyCallbackOperator,
                },
                self.event,
            )
            return op
        else:
            op = get_event_operator(
                {
                    "": OnUpstreamEventOperator,
                    OnCancelOperator.event_type: OnCancelOperator,
                    OnInputOperator.event_type: OnInputOperator,
                    OnCreatedOperator.event_type: OnCreatedOperator,
                }
            )
            return op


class OnUpstreamEventOperator(EventOperator):
    """
    上游事件的默认处理逻辑.
    """

    event_type: ClassVar[str] = ""
    default_state: ClassVar[str] = TaskState.WAITING.value

    def handle_event(self, g: "Ghost") -> Optional["Operator"]:
        session = g.session()
        task = session.task()
        # 思考轮次设置为 0.
        task.think_turns = 0
        thread = session.thread()
        thread.new_round(self.event)
        session.update_task(task, thread, update_history=False)
        return g.utils().handle_event(self.event)

    def default_action(self, g: "Ghost") -> Optional["Operator"]:
        session = g.session()
        task = session.task()
        # 默认 await.
        task.state = self.default_state
        session.update_task(task, update_history=True)
        return None

    def run(self, g: "Ghost") -> Optional["Operator"]:
        op = self.handle_event(g)
        if op is not None:
            return op
        return self.default_action(g)


class OnSelfEventOperator(EventOperator):
    """
    自己触发的事件的处理逻辑.
    """
    event_type: ClassVar[str] = ""
    default_state: ClassVar[str] = TaskState.WAITING.value

    def handle_event(self, g: "Ghost") -> Optional["Operator"]:
        session = g.session()
        task = session.task()
        # 思考轮次设置为 0.
        task.think_turns += 1
        thread = session.thread()
        thread.new_round(self.event)
        if task.think_too_much():
            session.update_task(task, thread, update_history=True)
            # 不再运行思考. 只是追加信息. 必须等待上游的输入才能继续运行.
            # todo: 是否要通知上游, ask to continue.
            return None
        session.update_task(task, thread, update_history=False)
        return g.utils().handle_event(self.event)

    def default_action(self, g: "Ghost") -> Optional["Operator"]:
        session = g.session()
        task = session.task()
        # 默认 await.
        task.state = self.default_state
        session.update_task(task, update_history=True)
        return None

    def run(self, g: "Ghost") -> Optional["Operator"]:
        op = self.handle_event(g)
        if op is not None:
            return op
        return self.default_action(g)


class OnCallbackEventOperator(EventOperator):
    """
    子任务触发的事件.
    """
    event_type: ClassVar[str] = ""

    def receive_event(self, g: "Ghost") -> bool:
        session = g.session()
        task = session.task()
        # 思考轮次设置为 0.
        thread = session.thread()
        thread.new_round(self.event)
        session.update_task(task, thread, update_history=False)
        return task.is_dead()

    def handle_event(self, g: "Ghost") -> Optional["Operator"]:
        return g.utils().handle_event(self.event)

    def run(self, g: "Ghost") -> Optional["Operator"]:
        # 接受事件.
        dead = self.receive_event(g)
        if dead:
            # 不处理逻辑了.
            return None
        # 处理事件.
        op = self.handle_event(g)
        if op is not None:
            return op
        # 不变更任何状态.
        return None


# --- upstream event operators --- #

class OnInputOperator(OnUpstreamEventOperator):
    """
    接受到上游的输入.
    """
    event_type: ClassVar[str] = DefaultEventType.INPUT.value
    default_state: ClassVar[str] = TaskState.WAITING.value


class OnCreatedOperator(OnUpstreamEventOperator):
    """
    接受到创建任务的消息.
    """
    event_type: ClassVar[str] = DefaultEventType.CREATED.value
    default_state: ClassVar[str] = TaskState.WAITING.value


class OnCancelOperator(OnUpstreamEventOperator):
    event_type = DefaultEventType.CANCELING.value
    default_state: ClassVar[str] = TaskState.CANCELLED.value

    def handle_event(self, g: "Ghost") -> Optional["Operator"]:
        session = g.session()
        task = session.task()
        if task.is_dead():
            # 不做额外处理.
            return None
        return super().handle_event(g)

    def default_action(self, g: "Ghost") -> Optional["Operator"]:
        session = g.session()
        task = session.task()
        # 取消所有的子任务.
        if task.children:
            g.utils().cancel_children_tasks(
                reason=f"parent task {task.task_id} is canceled",
                self_task=task,
            )
        return super().default_action(g)


# --- self event operators --- #

class OnThinkOperator(OnSelfEventOperator):
    event_type: ClassVar[str] = DefaultEventType.THINK.value
    default_state: ClassVar[str] = TaskState.WAITING.value


# --- call back operators --- #

class OnFinishCallbackOperator(OnCallbackEventOperator):
    event_type: ClassVar[str] = DefaultEventType.FINISH_CALLBACK

    def handle_event(self, g: "Ghost") -> Optional["Operator"]:
        session = g.session()
        task = session.task()
        from_task_id = self.event.from_task_id
        if from_task_id:
            group = task.on_callback_task(from_task_id)
            if group is not None:
                return g.utils().handle_event(self.event)
        return None


class OnFailureCallbackOperator(OnCallbackEventOperator):
    event_type: ClassVar[str] = DefaultEventType.FAILURE_CALLBACK

    def handle_event(self, g: "Ghost") -> Optional["Operator"]:
        # 好像没有什么额外的逻辑.
        return super().handle_event(g)


class OnWaitCallbackOperator(OnCallbackEventOperator):
    event_type: ClassVar[str] = DefaultEventType.WAIT_CALLBACK

    def handle_event(self, g: "Ghost") -> Optional["Operator"]:
        # 好像没有什么额外的逻辑.
        return super().handle_event(g)


class OnNotifyCallbackOperator(OnCallbackEventOperator):
    event_type: ClassVar[str] = DefaultEventType.NOTIFY_CALLBACK

    def handle_event(self, g: "Ghost") -> Optional["Operator"]:
        # 不会执行 event.
        return None
