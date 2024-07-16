from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from ghostiss.entity import EntityMeta
from ghostiss.helpers import uuid


class Process(BaseModel):
    process_id: str
    ghost_id: str
    thread_id: str
    task_id: str
    ghost_meta: EntityMeta
    shell_meta: EntityMeta
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)


class TaskState(str, Enum):
    NEW = "new"
    """the task is created"""

    RUNNING = "running"
    """the task is running"""

    WAITING = "waiting"
    """the task needs more inputs"""

    QUEUED = "queued"
    """the task is queued to run"""

    DEPENDING = "depending"
    """the task depends on other tasks"""

    # BREAKING = "breaking"
    YIELDING = "yielding"
    """the task yields to other task"""

    CANCELLED = "cancelled"
    FAILED = "failed"
    FINISHED = "finished"

    def is_dead(self, state: str) -> bool:
        return state in {self.FINISHED, self.FAILED, self.CANCELLED}


# class TaskBrief(BaseModel):
#     name: str
#     task_id: str
#     description: str = Field(description="")
#     requires: Optional[str] = Field(description="")
#     created: datetime = Field(default_factory=datetime.now)
#     updated: datetime = Field(default_factory=datetime.now)
#
#
# class TaskRelation(BaseModel):
#     yield_to: Optional[str] = Field(default=None)
#     depending_tasks: List[str] = Field(default_factory=list)
#     callback_tasks: List[str] = Field(default_factory=list)
#
#
# class TaskMindInfo(BaseModel):
#     meta: MetaData
#     step: str = Field(default="", description="mind step")
#     stack: List[str] = Field(default_factory=list)


class Task(BaseModel):
    # -- scope --- #
    process_id: str
    thread_id: str
    task_id: str = Field(default_factory=uuid, description="")
    run_id: str = Field(description="")
    parent_task: Optional[str] = Field(default=None)

    # --- brief --- #
    name: str
    description: str = Field(description="")
    requires: Optional[str] = Field(description="")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # --- relations --- #
    yield_to: Optional[str] = Field(default=None)
    depending_tasks: List[str] = Field(default_factory=list)
    callback_tasks: List[str] = Field(default_factory=list)

    # --- mind --- #
    idea: EntityMeta = Field(description="")

    # --- state --- #
    state: TaskState

    @classmethod
    def new(cls, process_id: str, thread_id: str, name: str, desc: str, mind_meta: EntityMeta, **kwargs) -> 'Task':
        kwargs["process_id"] = process_id
        kwargs["thread_id"] = thread_id
        kwargs["mind_meta"] = mind_meta
        kwargs["name"] = name
        kwargs["description"] = desc
        return cls(**kwargs)


class Runtime(ABC):

    # --- process --- #

    @abstractmethod
    def process(self) -> Process:
        pass

    @abstractmethod
    def save_process(self, p: Process) -> bool:
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Task]:
        pass

    @abstractmethod
    def save_task(self, task: Task) -> Task:
        pass

    @abstractmethod
    def lock_task(self, task_id: str) -> Optional[str]:
        pass

    @abstractmethod
    def release_task(self, task_id: str, locker: str) -> None:
        pass

    @abstractmethod
    def put_task_event(self, task_id: str, e: EntityMeta) -> None:
        pass

    @abstractmethod
    def save_all(self) -> None:
        pass
