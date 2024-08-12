from typing import List, Optional, Dict
from abc import ABC, abstractmethod
from enum import Enum
from ghostiss.entity import EntityMeta, Entity, EntityFactory
from pydantic import BaseModel, Field
from ghostiss.core.messages.message import Message
from ghostiss.helpers import uuid

__all__ = [
    'Event', 'EventFactory', 'EventBus', 'DefaultEventType',
]

EVENT_ENTITY_TYPE = "ghostiss.core.session.events.Event"


class Event(BaseModel, Entity):
    """
    Tasks communicate each others by Event.
    Event shall dispatch by EventBus.
    System use the Event popped from EventBus to restore a Session,
    Session.task() shall handle the Event, change the session state, and maybe fire more events.
    """
    block: bool = Field(
        description="whether the target task shall be locked by this event.",
    )
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
    priority: float = Field(
        default=0, description="priority of this event", min_items=0.0, max_items=1.0,
    )
    messages: List[Message] = Field(
        default_factory=list,
        description="list of messages sent by this event",
    )
    payloads: Dict[str, Dict] = Field(
        default_factory=dict,
        description="more structured data that follow the message.Payload pattern",
    )

    def event_type(self) -> str:
        return self.type

    def default_handler(self) -> str:
        return f"on_{self.event_type()}"

    def to_entity_meta(self) -> EntityMeta:
        return EntityMeta(
            id=self.id,
            type=EVENT_ENTITY_TYPE,
            data=self.model_dump(exclude={'id'}, exclude_defaults=True)
        )


class DefaultEventType(str, Enum):
    """
    默认的消息类型.
    """
    CREATED = "created"
    """任务刚刚被创建出来"""

    INPUT = "input"
    """外部对当前 task 的输入. """

    THINK = "think"
    """自我驱动的思考"""

    FINISH_CALLBACK = "finish_callback"
    """第三方 task 运行正常, 返回的消息. """

    FAILURE_CALLBACK = "failure_callback"
    """第三方 task 运行失败, 返回的消息. """

    WAIT_CALLBACK = "wait_callback"
    """Child task 返回消息, 期待更多的输入. """

    FINISHED = "finished"
    """任务结束时, 触发的事件. 可用于反思."""

    CANCELED = "cancelled"
    """任务取消时, 触发的事件. 可用于反思. """

    FAILED = "failed"
    """任务失败时, 触发的事件. 可用于反思."""

    INTERCEPT = "intercept"
    """对输入消息的拦截. 可以做预处理. """

    def block(self) -> bool:
        return self not in {
            DefaultEventType.INTERCEPT,
        }

    def new(
            self, *,
            task_id: str,
            from_task_id: Optional[str] = None,
            eid: Optional[str] = None,
            messages: List[Message],
            priority: float = 0.0,
    ) -> Event:
        id_ = eid if eid else uuid()
        type_ = str(self.value)
        return Event(
            type=type_, task_id=task_id, block=self.block(),
            id=id_, from_task_id=from_task_id, priority=priority,
            messages=messages,
        )


class EventFactory(EntityFactory):
    """
    使用 entity meta 反向生成 Event 实例.
    """

    def new_entity(self, meta_data: EntityMeta) -> Optional[Event]:
        type_ = meta_data['type']
        if type_ != EVENT_ENTITY_TYPE:
            return None
        id_ = meta_data['id']
        data = meta_data['data']
        data['id'] = id_
        return Event(**data)

    def force_new_event(self, meta_data: EntityMeta) -> Event:
        e = self.new_entity(meta_data)
        if e is None:
            raise ValueError(f"Could not create event for {meta_data}")
        return e


class EventBus(ABC):

    @abstractmethod
    def send_event(self, e: Event, max_count: int, priority: float = 0.0) -> None:
        pass

    @abstractmethod
    def pop_task_event(self, task_id: str) -> Optional[Event]:
        pass

    @abstractmethod
    def pop_global_event(self) -> Optional[Event]:
        pass
