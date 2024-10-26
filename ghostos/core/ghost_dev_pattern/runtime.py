from abc import ABC, abstractmethod
from typing import (
    Protocol, Self, Generic, Type, TypeVar, Tuple, Callable, Union, Optional, List, Literal, Dict
)
from .concepts import Context, Task, Func
from ghostos.container import Container
from ghostos.core.session import Session, Event
from ghostos.entity import EntityMeta
from pydantic import BaseModel, Field


class StackFrame(BaseModel):
    frame_id: str = Field(
        description="Ghost Stack Frame ID",
    )
    process_id: str = Field(
        description="Ghost always run in a certain process"
    )
    args: EntityMeta = Field(
        description="the arguments passed to the ghost function"
    )
    depth: int = Field(
        default=0,
        description="the depth of the stack"
    )
    state: EntityMeta = Field(
        description="the state data of the current ghost function stack frame",
    )
    returns: Optional[EntityMeta] = Field(
        default=None,
        description="the return values of the ghost function destination",
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="parent stack frame ID which create this frame. None for root frame",
    )
    event_id: Optional[str] = Field(
        default=None,
        description="the event id which create this frame. None for root frame",
    )
    status: Literal["done", "running", "waiting", "pending", "aborted", "cancelled", "new"] = Field(
        default="new",
        description="the status of the stack frame",
    )
    description: str = Field(
        default="",
        description="description of the stack frame current status"
    )
    children: Dict[str, str] = Field(
        default_factory=dict,
        description="sub stack frame index. from sub task name to frame ids",
    )


class Runtime(Protocol):
    container: Container
    session: Session

    @abstractmethod
    def get_frame(self, frame_id: str) -> Optional[StackFrame]:
        pass

