import uuid
from abc import ABC, abstractmethod
from enum import Enum

from typing import TYPE_CHECKING, Optional, List
from pydantic import BaseModel, Field
from ghostiss.meta import MetaData
from ghostiss.context import Context

if TYPE_CHECKING:
    from ghostiss.interfaces.threads import Inputs
    from ghostiss.interfaces.thoughts import Event, TaskOverflow


class Process(BaseModel):
    agent_id: str
    process_id: str
    source_code: MetaData = Field(description="Agent Source code")

    @classmethod
    def new(cls, source_code: MetaData) -> "Process":
        return cls(id=source_code.id, source_code=source_code, process_id=uuid.uuid4().hex)


class NewTask(BaseModel):
    process_id: str
    thread_id: str
    thought: MetaData = Field(description="Task Thought")


class TaskState(str, Enum):
    RUNNING = "running"
    WAITING = "waiting"
    DEPENDING = "depending"
    QUEUED = "queued"


class Task(BaseModel):
    process_id: str
    task_id: str
    thread_id: str
    state: str = Field(default=TaskState.WAITING, description="task state")
    locker: Optional[str] = Field(default=None)
    thought: MetaData = Field(description="Task Thought")

    depend_on: List[str] = Field(default_factory=list, description="depend on")
    callbacks: List[str] = Field(default_factory=list, description="callbacks")

    def is_locked(self) -> bool:
        return self.locker is not None


class Runtime(ABC):

    @abstractmethod
    def get_process(self, ctx: Context, process_id: str) -> Optional[Process]:
        pass

    @abstractmethod
    def create_process(self, ctx: Context, source_code: MetaData) -> Process:
        pass

    @abstractmethod
    def remove_process(self, ctx: Context, process_id: str) -> None:
        pass

    @abstractmethod
    def get_agent_process(self, ctx: Context, agent_id: str) -> Optional[Process]:
        pass

    @abstractmethod
    def get_task(self, ctx: Context, task_id: str, lock: bool = False) -> Optional[Task]:
        pass

    @abstractmethod
    def lock_task(self, ctx: Context, task_id: str) -> Optional[str]:
        pass

    @abstractmethod
    def unlock_task(self, ctx: Context, task_id: str, locker: str) -> bool:
        pass

    @abstractmethod
    def push_task_inputs(self, ctx: Context, task_id: str, inputs: "Inputs") -> Optional[TaskOverflow]:
        """
        被动队列.
        """
        pass

    @abstractmethod
    def pop_threads_inputs(self) -> Optional[Inputs]:
        pass

    @abstractmethod
    def pop_thread_queued_task(self, thread_id: str) -> Optional[Task]:
        """
        返回 thread 的一个排队的 task. 并且同时加锁.
        """
        pass

    @abstractmethod
    def pop_task_inputs(self, ctx: Context, task: Task) -> Optional["Inputs"]:
        """
        从被动队列里吐出一个消息.
        """
        pass

    @abstractmethod
    def create_task(self, ctx: Context, new_task: NewTask) -> Task:
        """
        todo: 记得带锁.
        """
        pass

    @abstractmethod
    def update_task(self, ctx: Context, task: Task) -> None:
        pass
