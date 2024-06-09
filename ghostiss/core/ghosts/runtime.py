from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from ghostiss.meta import MetaData


class Process(BaseModel):
    process_id: str
    root_thread_id: str
    root_task_id: str
    ghost_meta: MetaData


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


class TaskBrief(BaseModel):
    name: str
    task_id: str
    description: str = Field(description="")
    requires: Optional[str] = Field(description="")
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)


class TaskRelation(BaseModel):
    yield_to: Optional[str] = Field(default=None)
    depending_tasks: List[str] = Field(default_factory=list)
    callback_tasks: List[str] = Field(default_factory=list)


class Task(BaseModel):
    # -- scope --- #
    process_id: str
    thread_id: str
    task_id: str = Field(description="")
    run_id: str = Field(description="")
    parent_task: Optional[str] = Field(default=None)

    # --- brief --- #
    name: str
    description: str = Field(description="")
    requires: Optional[str] = Field(description="")
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    # --- relations --- #
    yield_to: Optional[str] = Field(default=None)
    depending_tasks: List[str] = Field(default_factory=list)
    callback_tasks: List[str] = Field(default_factory=list)

    # --- mind --- #
    mind_meta: MetaData

    # --- state --- #
    state: TaskState


class Runtime(ABC):

    @abstractmethod
    def process(self) -> Process:
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Task]:
        pass

    @abstractmethod
    def save_task(self, task: Task) -> Task:
        pass

    @abstractmethod
    def list_process_tasks(self, process_id: str) -> List[TaskBrief]:
        pass

    @abstractmethod
    def save_all(self) -> None:
        pass
