from typing import List, Optional
from abc import ABC, abstractmethod
from enum import Enum
from importlib import import_module
from ghostiss.entity import EntityMeta, Entity, EntityFactory
from pydantic import BaseModel, Field
from ghostiss.core.messages.message import Message
from ghostiss.helpers import uuid
from ghostiss.core.moss.exports import Exporter

__all__ = [
    'Event', 'EventFactory', 'EventBus', 'DefaultEventType',
]


class Event(BaseModel, Entity):
    """
    事件机制.
    """
    id: str = Field(default_factory=uuid, description="event id")
    type: str = Field(default="", description="event type")
    task_id: str = Field(description="task id in which this event shall be handled")
    from_task_id: Optional[str] = Field(default=None, description="task id in which this event is fired")
    priority: float = Field(default=0, description="priority of this event", min_items=0.0, max_items=1.0)
    instruction: Optional[str] = Field(default=None, description="event instruction")
    messages: List[Message] = Field(default_factory=list)

    def event_type(self) -> str:
        return self.type

    def default_handler(self) -> str:
        return f"on_{self.event_type()}"

    def to_entity_meta(self) -> EntityMeta:
        cls = self.__class__
        entity_type = f"{cls.__module__}:{cls.__name__}"
        return EntityMeta(
            id=self.id,
            type=entity_type,
            data=self.model_dump(exclude={'id'})
        )


class DefaultEventType(str, Enum):
    """
    默认的消息类型.
    """

    INPUT = "input"
    """外部对当前 task 的输入. """

    CANCEL = "cancel"
    """当前任务"""

    THINK = "think"
    """自我驱动的思考"""

    FINISHED = "finished"
    """任务结束时"""

    FINISH_CALLBACK = "finish_callback"
    """第三方 task 运行正常, 返回的消息. """

    FAILURE_CALLBACK = "failure_callback"
    """第三方 task 运行失败, 返回的消息. """

    WAIT_CALLBACK = "wait_callback"
    """Child task 返回消息, 期待更多的输入. """

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
            id=id_, type=type_, task_id=task_id, from_task_id=from_task_id, priority=priority,
            messages=messages,
        )


class OnCreate(Event):

    def event_type(self) -> str:
        return "create"


class OnFinish(Event):

    def event_type(self) -> str:
        return "finish"


class EventFactory(EntityFactory[Event]):

    def new_entity(self, meta_data: EntityMeta) -> Optional[Event]:
        parts = meta_data['type'].split(':', 2)
        if len(parts) != 2:
            return None
        module, spec = parts[0], parts[1]
        imported_module = import_module(module)
        if imported_module is None:
            return None
        model = imported_module[spec]
        if model is None or not issubclass(model, Event):
            # todo: raise
            return None
        data = meta_data['data']
        data['id'] = meta_data['id']
        return model(**data)

    def force_new_event(self, meta_data: EntityMeta) -> Event:
        e = self.new_entity(meta_data)
        if e is None:
            raise ValueError(f"Could not create event for {meta_data}")
        return e


class EventBus(ABC):

    @abstractmethod
    def send_event(self, e: Event) -> None:
        pass

    @abstractmethod
    def pop_task_event(self, task_id: str) -> Optional[Event]:
        pass

    @abstractmethod
    def pop_global_event(self) -> Optional[Event]:
        pass


EXPORTS = Exporter().\
    source_code(Event).\
    interface(EventBus).\
    interface(EventFactory)

