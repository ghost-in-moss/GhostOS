import enum
import time
from typing import Optional, Dict, Any, ClassVar, Set, NamedTuple, Iterable
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from ghostiss.core.messages.openai import (
    OPENAI_MESSAGE_TYPES,
)

__all__ = ["Message", "Caller", "Role", "Header"]


class Role(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"
    TOOL = "tool"

    @classmethod
    def all(cls) -> Set[str]:
        return set(map(lambda x: x.value, cls))


class Header(BaseModel):
    """
    消息体的首包.
    """
    id: str = Field(default="")
    type: str = Field(default="", description="Message type")
    role: str = Field(default="", description="Message role")
    name: str = Field(default="", description="Message sender name")


class Message(BaseModel, ABC):
    """
    消息体的容器. 通用的抽象设计.
    重点是实现不同类型的消息体, 把角色等讯息当成通用的.
    """

    msg_type: ClassVar[str] = ""

    # --- header --- #

    id: str = Field(default="")
    role: str = Field(default="", description="Message role", enum=Role.all())
    name: Optional[str] = Field(default=None, description="Message sender name")
    created: int = Field(default_factory=lambda: int(time.time()), description="Message creation time")

    # --- attachments --- #

    attachments: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_header(cls, header: Header) -> "Message":
        info = header.model_dump()
        return cls(**info)

    def update_from_header(self, header: Header) -> None:
        data = header.model_dump()
        for k, v in data.items():
            if not v:
                # header 的空值跳过.
                continue
            setattr(self, k, v)

    @abstractmethod
    def as_openai_message(self) -> Iterable[OPENAI_MESSAGE_TYPES]:
        """
        以 openai 的消息协议, 返回一个可展示的消息.
        """
        pass

    @abstractmethod
    def as_openai_memory(self) -> Iterable[OPENAI_MESSAGE_TYPES]:
        """
        以 openai 的消息协议, 返回一个 memory 消息.
        通常就是 as_openai_message
        """
        pass


class Caller(Message):
    """
    对上游进行请求的消息.
    需要被摘出来.
    """
    id: str = Field(description="caller id")
    msg_type: ClassVar[str] = "caller"
    name: str = Field(description="Caller name")
    arguments: str = Field(description="Caller arguments")

    def as_openai_message(self) -> Iterable[OPENAI_MESSAGE_TYPES]:
        return []

    def as_openai_memory(self) -> Iterable[OPENAI_MESSAGE_TYPES]:
        """
        """
        return []
