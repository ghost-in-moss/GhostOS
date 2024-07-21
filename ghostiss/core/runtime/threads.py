from typing import Optional, List, Iterable, ClassVar
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from ghostiss.core.messages import Message, Payload
from ghostiss.core.moss.context import PyContext

__all__ = [
    'Threads', 'Thread', 'ThreadPayload',
]


class ThreadPayload(Payload):
    key: ClassVar[str] = "thread"

    thread_id: str = Field(description="Thread ID")


class Thread(BaseModel):
    """
    对话历史的快照.
    """
    id: str = Field(
        description="The id of the thread",
    )
    root_id: Optional[str] = Field(
        default=None,
        description="The id of the root thread if the thread is a fork",
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="The id of the parent thread if the thread is a fork",
    )

    messages: List[Message] = Field(
        default_factory=list,
    )
    inputs: List[Message] = Field(
        default_factory=list,
    )
    appending: List[Message] = Field(
        default_factory=list,
    )

    pycontext: PyContext = Field(
        description="The PyContext instance",
    )

    def get_pycontext(self) -> PyContext:
        # todo: iterate messages and add variable message
        return self.pycontext

    def update(self, messages: Iterable[Message], pycontext: Optional[PyContext] = None) -> "Thread":
        thread = self.model_copy()
        if messages:
            thread.appending.extend(messages)
        if pycontext is not None:
            thread.pycontext = thread.pycontext.join(pycontext)
        # todo: 验证没有复制污染.
        return thread


class Threads(ABC):

    @abstractmethod
    def get_thread(self, thread_id: str, create: bool = False) -> Optional[Thread]:
        pass

    @abstractmethod
    def create_thread(self, messages: List[Message], pycontext: PyContext, thread_id: Optional[str] = None) -> Thread:
        pass

    @abstractmethod
    def update_thread(self, thread: Thread) -> Thread:
        pass

    @abstractmethod
    def fork_thread(self, thread: Thread) -> Thread:
        pass
