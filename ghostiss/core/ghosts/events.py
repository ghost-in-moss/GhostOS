from abc import ABC, abstractmethod
from typing import ClassVar, Type, List
from ghostiss.meta import BaseMetaClass, MetaClassLoader
from ghostiss.helpers import uuid
from pydantic import BaseModel, Field
from ghostiss.core.ghosts.runtime import Task


class Event(BaseMetaClass, ABC):
    event_kind: ClassVar[str]
    id: str = Field(default_factory=uuid, description="event id")
    task: Task = Field(description="event to the task")

    def meta_id(self) -> str:
        return self.id

    @classmethod
    def meta_kind(cls) -> str:
        return cls.event_kind


class EventLoader(MetaClassLoader[Event]):
    """
    with event type that can generate multiple event type by self.meta_new(meta_data)
    """

    def __init__(self, kinds: List[Type[Event]]):
        default_kinds = []
        super().__init__(default_kinds + kinds)
