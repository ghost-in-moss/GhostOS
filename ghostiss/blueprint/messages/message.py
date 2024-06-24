import enum
import time
from typing import Optional, Dict, Any, ClassVar, Set, Iterable, Union, TypeVar
from typing_extensions import Literal
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from ghostiss.helpers import uuid
from ghostiss.entity import EntityMeta, EntityClass

__all__ = ["Message", "Future", "Role", "FunctionCall", "ToolCall", "PACK", "Final", "first_pack"]


class Role(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"
    TOOL = "tool"

    @classmethod
    def all(cls) -> Set[str]:
        return set(map(lambda x: x.value, cls))


class FunctionCall(BaseModel):
    arguments: str
    name: str


class ToolCall(BaseModel):
    id: str
    """The ID of the tool call."""

    function: FunctionCall
    """The function that the model called."""

    type: Literal["function"]
    """The type of the tool. Currently, only `function` is supported."""


class Future(BaseModel):
    id: str
    """The ID of the tool call."""
    name: str
    arguments: str


class Message(EntityClass, BaseModel, ABC):
    """
    消息体的容器. 通用的抽象设计.
    重点是实现不同类型的消息体, 把角色等讯息当成通用的.
    """
    type: ClassVar[str]

    # --- header --- #

    msg_id: str = Field(default="")

    role: str = Field(default="", description="Message role", enum=Role.all())
    name: Optional[str] = Field(default=None, description="Message sender name")
    created: int = Field(default=0, description="Message creation time")

    # --- attachments --- #

    attachments: Optional[Dict[str, Any]] = Field(default=None, description="""
- attachments 不能是和记忆转换逻辑有关的. 
""")

    def to_entity_meta(self):
        return EntityMeta(
            id=self.msg_id,
            type=self.type,
            # !!exclude defaults
            data=self.model_dump(exclude_defaults=True),
        )

    @classmethod
    def entity_type(cls) -> str:
        return cls.type

    @classmethod
    def match(cls, meta: EntityMeta) -> bool:
        return meta["type"] == cls.type

    @classmethod
    def new_entity(cls, meta: EntityMeta) -> Optional["Message"]:
        if meta["type"] != cls.entity_type():
            return None
        try:
            return cls(**meta["data"])
        except TypeError:
            return None

    @abstractmethod
    def buff(self, pack: "PACK") -> bool:
        pass

    @abstractmethod
    def as_openai_message(self) -> Iterable[ChatCompletionMessageParam]:
        """
        以 openai 的消息协议, 返回可展示的消息.
        """
        pass

    @abstractmethod
    def as_openai_memory(self) -> Iterable[ChatCompletionMessageParam]:
        """
        以 openai 的消息协议, 返回 memory 消息.
        通常就是 as_openai_message
        """
        pass


PACK = Union[EntityMeta, Message]

M = TypeVar("M", bound=Message)


def first_pack(message: M) -> M:
    if not message.msg_id:
        message.msg_id = uuid()
    if not message.created:
        message.created = int(time.time())
    return message


class Final(Message):
    """
    流式消息的尾包.
    """
    type: ClassVar[str] = "ghostiss.messages.final"

    def buff(self, pack: "PACK") -> bool:
        return False

    def as_openai_message(self) -> Iterable[ChatCompletionMessageParam]:
        return []

    def as_openai_memory(self) -> Iterable[ChatCompletionMessageParam]:
        return []
