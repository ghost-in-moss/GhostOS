from typing import Optional, List, Iterable, ClassVar
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from ghostiss.core.messages import Message, Payload, copy_messages
from ghostiss.core.moss.context import PyContext
from ghostiss.core.runtime.llms import Chat
from ghostiss.helpers import uuid

__all__ = [
    'Threads', 'MsgThread', 'ThreadPayload',
    'thread_to_chat',
]


class ThreadPayload(Payload):
    key: ClassVar[str] = "thread"

    thread_id: str = Field(description="Thread ID")


class MsgThread(BaseModel):
    """
    对话历史的快照.
    """
    id: str = Field(
        default_factory=uuid,
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
        default_factory=PyContext,
        description="The PyContext instance",
    )

    def get_pycontext(self) -> PyContext:
        # todo: iterate messages and add variable message
        return self.pycontext

    def fork(self, tid: Optional[str] = None) -> "MsgThread":
        tid = tid if tid else uuid()
        root_id = self.root_id if self.root_id else self.id
        parent_id = self.id
        return self.model_copy(update=dict(id=tid, root_id=root_id, parent_id=parent_id), deep=True)

    def update(self, messages: Iterable[Message], pycontext: Optional[PyContext] = None) -> None:
        """
        更新当前的 Thread.
        :param messages:
        :param pycontext:
        :return:
        """
        if messages:
            self.appending.extend(messages)
        if pycontext is not None:
            self.pycontext = self.pycontext.join(pycontext)

    def thread_copy(self, update: Optional[dict] = None) -> "MsgThread":
        return self.model_copy(update=update, deep=True)

    def updated(self) -> "MsgThread":
        """
        返回一个新的 Thread, inputs 和 appending 都追加到 messages 里.
        :return:
        """
        thread = self.model_copy(deep=True)
        if thread.inputs:
            thread.messages.extend(thread.inputs)
            thread.inputs = []
        if thread.appending:
            thread.messages.extend(thread.appending)
            thread.appending = []
        return thread


def thread_to_chat(chat_id: str, system: List[Message], thread: MsgThread) -> Chat:
    """
    将 thread 转换成基准的 chat.
    :param chat_id:
    :param system:
    :param thread:
    :return:
    """
    chat = Chat(
        id=chat_id,
        system=system,
        history=copy_messages(thread.messages),
        inputs=copy_messages(thread.inputs),
        appending=copy_messages(thread.appending),
    )
    return chat


class Threads(ABC):

    @abstractmethod
    def get_thread(self, thread_id: str, create: bool = False) -> Optional[MsgThread]:
        pass

    @abstractmethod
    def create_thread(self, messages: List[Message], pycontext: PyContext, thread_id: Optional[str] = None) -> MsgThread:
        pass

    @abstractmethod
    def update_thread(self, thread: MsgThread) -> MsgThread:
        pass

    @abstractmethod
    def fork_thread(self, thread: MsgThread) -> MsgThread:
        pass
