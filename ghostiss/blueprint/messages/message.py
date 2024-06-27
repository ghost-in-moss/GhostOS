import enum
import time
from typing import Optional, Dict, Any, ClassVar, Set, Iterable, Union, TypeVar, NamedTuple, TypedDict, List, Type
from typing_extensions import Literal, Required
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from ghostiss.helpers import uuid

__all__ = [
    "Message", "Caller", "Role", "DefaultTypes",
    "FunctionCall", "FunctionalToken",
]


class Role(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"

    @classmethod
    def all(cls) -> Set[str]:
        return set(map(lambda x: x.value, cls))


class FunctionCall(BaseModel):
    arguments: str
    name: str


class FunctionalToken(BaseModel):
    id: str
    token: str
    function: FunctionCall
    deliver: bool


class DefaultTypes(str, enum.Enum):
    DEFAULT = ""
    CHAT_COMPLETION = "chat_completion"

    def new(
            self, *, content: str, role: str = "assistant", memory: Optional[str] = None, name: Optional[str] = None,
    ) -> "Message":
        return Message(content=content, memory=memory, name=name, type=self.value, role=role)


class Caller(TypedDict, total=False):
    id: Optional[str]
    name: Required[str]
    arguments: Required[str]


class Message(BaseModel):
    """
    消息体的容器. 通用的抽象设计.
    """

    msg_id: str = Field(default="")
    type: str = Field(default="", description="消息类型是对 payload 的约定. 默认的 type就是 text.")
    created: int = Field(default=0, description="Message creation time")
    pack: bool = Field(default=True, description="Message reset time")

    role: str = Field(default="", description="Message role", enum=Role.all())
    name: Optional[str] = Field(default=None, description="Message sender name")

    content: Optional[str] = Field(default=None, description="Message content")
    memory: Optional[str] = Field(default=None, description="Message memory")

    # --- attachments --- #

    payload: Dict[str, Dict] = Field(default_factory=dict, description="k/v 结构的强类型参数.")
    attachments: Dict[str, List[Dict]] = Field(default_factory=dict, description="k/list[v] 类型的强类型参数.")

    @classmethod
    def new(
            cls, *,
            role: str,
            type_: str = "",
            content: Optional[str] = None,
            memory: Optional[str] = None,
            name: Optional[str] = None,
            msg_id: Optional[str] = None,
            created: int = 0,
    ):
        if msg_id is None:
            msg_id = uuid()
        if created <= 0:
            created = int(time.time())
        if role is None:
            role = Role.ASSISTANT.value
        return cls(
            role=role, name=name, content=content, memory=memory, pack=False,
            type=type_,
            msg_id=msg_id, created=created,
        )

    @classmethod
    def new_pack(
            cls, *,
            type_: str = "",
            role: Optional[str] = None,
            content: Optional[str] = None,
            memory: Optional[str] = None,
            name: Optional[str] = None,
    ):
        return cls(
            role=role, name=name, content=content, memory=memory, pack=True,
            type=type_,
        )

    def get_content(self) -> Optional[str]:
        if self.memory is None:
            return self.content
        return self.memory

    def buff(self, pack: "Message") -> bool:
        if pack.get_type() != self.get_type():
            return False
        if pack.msg_id and self.msg_id and pack.msg_id != self.msg_id:
            return False
        if not pack.pack:
            self.reset(pack)
            return True
        self.update(pack)
        return True

    def reset(self, pack: "Message") -> None:
        self.msg_id = pack.msg_id
        self.type = pack.type
        self.created = pack.created
        self.pack = False
        self.role = pack.role
        self.name = pack.name
        self.content = pack.content
        self.memory = pack.memory
        self.payload = pack.payload
        self.attachments = pack.attachments

    def get_copy(self) -> "Message":
        return self.model_copy()

    def update(self, pack: "Message") -> None:
        if not self.msg_id:
            self.msg_id = pack.msg_id
        if not self.type:
            self.type = pack.type
        if not self.role:
            self.role = pack.role
        if self.name is None:
            self.name = pack.name

        if self.content is None:
            self.content = pack.content
        elif pack.content is not None:
            self.content += pack.content

        if pack.memory is not None:
            self.memory = pack.memory

        self.payload.update(pack.payload)

        if pack.attachments is not None:
            for key, items in pack.attachments.items():
                saved = self.attachments.get(key, [])
                saved.append(*items)
                self.attachments[key] = saved

    def get_type(self) -> str:
        return self.type or DefaultTypes.DEFAULT

    def dump(self) -> Dict:
        return self.model_dump(exclude_defaults=True)


