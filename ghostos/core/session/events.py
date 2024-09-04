from typing import List, Optional, Dict
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel, Field
from ghostos.core.messages.message import Message
from ghostos.helpers import uuid
from contextlib import contextmanager

__all__ = [
    'Event', 'EventBus', 'DefaultEventType',
]

EVENT_ENTITY_TYPE = "ghostos.core.session.events.Event"


class Event(BaseModel):
    """
    Tasks communicate each others by Event.
    Event shall dispatch by EventBus.
    System use the Event popped from EventBus to restore a Session,
    Session.task() shall handle the Event, change the session state, and maybe fire more events.
    """

    task_id: str = Field(
        description="task id of which this event shall send to.",
    )
    type: str = Field(
        default="",
        description="event type, by default the handler shall named on_{type}"
    )

    id: str = Field(
        default_factory=uuid,
        description="event id",
    )

    from_task_id: Optional[str] = Field(
        default=None,
        description="task id in which this event is fired",
    )
    from_task_name: Optional[str] = Field(
        default=None,
        description="task name in which this event is fired",
    )
    reason: str = Field(
        default="",
        description="reason of the event.",
    )
    instruction: str = Field(
        default="",
        description="instruction from the event telling what to do.",
    )
    messages: List[Message] = Field(
        default_factory=list,
        description="list of messages sent by this event",
    )
    payloads: Dict[str, Dict] = Field(
        default_factory=dict,
        description="more structured data that follow the message.Payload pattern",
    )
    callback: bool = Field(
        default=False,
        description="if the event is a callback from child task to parent task.",
    )

    def from_self(self) -> bool:
        """
        通过任务是否是自己触发的, 来判断是否要继续.
        """
        return self.task_id == self.from_task_id

    def no_reason_or_instruction(self) -> bool:
        return not self.reason and not self.instruction

    def default_handler(self) -> str:
        return f"on_{self.event_type()}"

    @classmethod
    def new(
            cls, *,
            event_type: str,
            task_id: str,
            messages: List[Message],
            from_task_id: Optional[str] = None,
            reason: str = "",
            instruction: str = "",
            eid: Optional[str] = None,
            payloads: Optional[Dict] = None,
    ) -> "Event":
        id_ = eid if eid else uuid()
        type_ = event_type
        payloads = payloads if payloads is not None else {}
        return cls(
            id=id_,
            type=type_,
            task_id=task_id,
            from_task_id=from_task_id,
            reason=reason,
            instruction=instruction,
            messages=messages,
            payloads=payloads,
        )


class DefaultEventType(str, Enum):
    """
    默认的消息类型.
    """
    CREATED = "created"
    """任务刚刚被创建出来"""

    INPUT = "input"
    """外部对当前 task 的输入. """

    OBSERVE = "observe"
    """自我驱动的思考"""

    CANCELING = "cancelling"
    """任务取消时, 触发的事件. 需要广播给子节点. """
    KILLING = "killing"

    FINISH_CALLBACK = "finish_callback"
    """child task 运行正常, 返回的消息. """

    FAILURE_CALLBACK = "failure_callback"
    """child task 运行失败, 返回的消息. """

    NOTIFY_CALLBACK = "notify_callback"
    """child task send some notice messages"""

    WAIT_CALLBACK = "wait_callback"
    """Child task 返回消息, 期待更多的输入. """

    FINISHED = "finished"
    """任务结束时, 触发的事件. 可用于反思."""

    FAILED = "failed"
    """任务失败时, 触发的事件. 可用于反思."""

    def block(self) -> bool:
        return self not in {}

    def new(
            self, *,
            task_id: str,
            messages: List[Message],
            from_task_id: Optional[str] = None,
            reason: str = "",
            instruction: str = "",
            eid: Optional[str] = None,
            payloads: Optional[Dict] = None,
    ) -> Event:
        type_ = str(self.value)
        payloads = payloads if payloads is not None else {}
        return Event.new(
            event_type=type_,
            task_id=task_id,
            from_task_id=from_task_id,
            reason=reason,
            instruction=instruction,
            messages=messages,
            eid=eid,
            payloads=payloads,
        )


class EventBus(ABC):
    """
    global event bus.
    """

    @abstractmethod
    def send_event(self, e: Event, notify: bool) -> None:
        """
        send an event to the event bus, and notify the task if it's Ture.
        !! Canceled event is higher priority.
        :param e: event to send
        :param notify: whether to notify the task
        """
        pass

    @abstractmethod
    def pop_task_event(self, task_id: str) -> Optional[Event]:
        """
        pop a task event by task_id.
        the canceled event has higher priority to others.
        :param task_id: certain task id.
        :return: event or None if timeout is reached
        """
        pass

    @abstractmethod
    def pop_task_notification(self) -> Optional[str]:
        """
        pop a task notification from the main queue.
        :return: task id or None if not found.
        """
        pass

    @abstractmethod
    def notify_task(self, task_id: str) -> None:
        """
        notify a task to check new events.
        :param task_id: task id
        """
        pass

    @abstractmethod
    def clear_task(self, task_id: str) -> None:
        pass

    @contextmanager
    def transaction(self):
        yield
