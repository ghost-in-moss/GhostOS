from abc import ABC
from typing import ClassVar, Type, List, Optional, Union
from ghostiss.entity import EntityMeta, BaseEntityClass, EntityClassLoader
from ghostiss.helpers import uuid
from pydantic import Field


class Event(BaseEntityClass, ABC):
    event_kind: ClassVar[str]
    id: str = Field(default_factory=uuid, description="event id")
    task_id: str
    from_task_id: str

    def entity_id(self) -> str:
        return self.id

    @classmethod
    def entity_kind(cls) -> str:
        return cls.event_kind


EVENT_TYPES = Union[Event, EntityMeta]


class OnInput(Event):
    """
    输入消息.
    """
    pass


class OnOutput(Event):
    """
    输入消息.
    """
    pass


class OnCallback(Event):
    """
    回调消息.
    """
    pass


class EventLoader(EntityClassLoader[Event]):
    """
    with event type that can generate multiple event type by self.meta_new(meta_data)
    """
    default_kinds: List[Type[Event]] = []

    def __init__(self, kinds: Optional[List[Type[Event]]] = None):
        kinds = kinds or self.default_kinds
        super().__init__(kinds)
