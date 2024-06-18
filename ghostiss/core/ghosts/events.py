from abc import ABC
from typing import ClassVar, Type, List, Optional, Union
from ghostiss.entity import Normalized, BaseEntityClass, EntityClassLoader
from ghostiss.helpers import uuid
from pydantic import Field


class Event(BaseEntityClass, ABC):
    event_kind: ClassVar[str]
    id: str = Field(default_factory=uuid, description="event id")

    def entity_id(self) -> str:
        return self.id

    @classmethod
    def entity_kind(cls) -> str:
        return cls.event_kind


EVENT_TYPES = Union[Event, Normalized]


class OnIntercept(Event):
    pass


class OnInput(Event):
    pass


class OnOutput(Event):
    pass


class OnThink(Event):
    pass


class OnCallback(Event):
    pass


class OnFinishCallback(Event):
    pass


class OnFailureCallback(Event):
    pass


class OnAwaitCallback(Event):
    pass


class OnOutputCallback(Event):
    pass


class EventLoader(EntityClassLoader[Event]):
    """
    with event type that can generate multiple event type by self.meta_new(meta_data)
    """
    default_kinds: List[Type[Event]] = []

    def __init__(self, kinds: Optional[List[Type[Event]]] = None):
        kinds = kinds or self.default_kinds
        super().__init__(kinds)
