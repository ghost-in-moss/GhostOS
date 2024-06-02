from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, Field
from ghostiss.context import Context
from ghostiss.messages import Message, Messenger
from ghostiss.interfaces.llms import Function


class Turn(BaseModel):
    turn_id: str
    run_id: str
    messages: List[Message]


class Inputs(BaseModel):
    """

    """
    inputs: List[Message]
    task_id: str = Field(default="")
    last_run_id: Optional[str] = Field(default=None)
    context: Optional[List[Turn]] = Field(default=None)
    functions: List[Function] = Field(default_factory=list)

    @classmethod
    def new_queued_run(cls, task_id: str) -> "Inputs":
        return Inputs(
            inputs=[],
            task_id=task_id,
        )


class Thread(BaseModel):
    thread_id: str
    run_id: str = Field(default="")


class ThreadRun(BaseModel):
    run_id: str
    process_id: str
    thread_id: str

    instructions: str = Field(description="")
    context: List[Turn] = Field(default_factory=list)
    inputs: Inputs


class Threads(ABC):

    @abstractmethod
    def get_thread(self, ctx: Context, thread_id: str) -> Optional[Thread]:
        pass

    @abstractmethod
    def create_thread(self, ctx: Context, thread_id: str, messages: Optional[List[Message]] = None) -> Thread:
        pass

    @abstractmethod
    def reset_thread_run(self, ctx: Context, thread: Thread, run_id: str) -> None:
        pass

    @abstractmethod
    def fork_thread(self, ctx: Context, thread: Thread, run_id: str) -> Thread:
        """
        使用 Thread 历史上的某个 run 创建一个新的 thread.
        """
        pass

    @abstractmethod
    def get_run(self, ctx: Context, t: Thread, inputs: Inputs) -> ThreadRun:
        pass

    @abstractmethod
    def update_run(self, ctx: Context, run: ThreadRun, outputs: List[Message]) -> Turn:
        pass

    @abstractmethod
    def append_turn(self, ctx: Context, thread_ids: List[str], messages: Turn) -> None:
        pass
