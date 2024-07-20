import enum
import time
from typing import Optional, Dict, Set, Iterable, Union, List, ClassVar
from abc import ABC
from pydantic import BaseModel, Field
from ghostiss.helpers import uuid

__all__ = [
    "Message", "Role", "DefaultTypes",
    "MessageClass",
    "MessageType", "MessageTypeParser",
    "FunctionalToken",
    "Payload", "Attachment", "Caller",
]


class Role(str, enum.Enum):
    """
    消息体的角色, 对齐了 OpenAI
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"

    @classmethod
    def all(cls) -> Set[str]:
        return set(map(lambda x: x.value, cls))


class DefaultTypes(str, enum.Enum):
    DEFAULT = ""
    CHAT_COMPLETION = "chat_completion"
    ERROR = "error"
    FINAL = "final"

    def new(
            self, *,
            content: str, role: str = Role.ASSISTANT.value, memory: Optional[str] = None, name: Optional[str] = None,
    ) -> "Message":
        return Message(content=content, memory=memory, name=name, type=self.value, role=role)

    def match(self, message: "Message") -> bool:
        return message.type == self.value

    @classmethod
    def final(cls):
        return Message(type=cls.FINAL.value, role=Role.ASSISTANT.value)

    @classmethod
    def is_final(cls, pack: "Message") -> bool:
        return pack.type == cls.FINAL.value

    @classmethod
    def is_protocol_type(cls, message: "Message"):
        return not message.pack and message.type in {cls.ERROR, cls.FINAL}


class Caller(BaseModel):
    """
    消息协议中用来描述一个工具或者function 的调用请求.
    """
    id: Optional[str] = Field(default=None, description="caller 的 id, 用来 match openai 的 tool call 协议. ")
    name: str = Field(description="方法的名字.")
    arguments: str = Field(description="方法的参数. ")
    protocol: bool = Field(default=True, description="caller 是否是基于协议生成的?")

    def add(self, message: "Message") -> None:
        message.callers.append(self)


class FunctionalToken(BaseModel):
    """
    定义特殊的 token, 用来在流式输出中生成 caller.
    """

    id: Optional[str] = Field(default=None, description="用来生成 caller 的 id.")
    token: str = Field(description="流式输出中标志 caller 的特殊 token. 比如 :moss>\n ")
    caller: str = Field(description="caller 的名字. ")
    description: str = Field(description="functional token 的描述")
    deliver: bool = Field(description="functional token 后续的信息是否要发送. 可以设置不发送. ")

    def new_caller(self, arguments: str) -> "Caller":
        return Caller(
            id=self.id,
            name=self.caller,
            arguments=arguments,
            protocol=False,
        )


class Payload(BaseModel, ABC):
    """
    消息体的可扩展的部分. 拥有强类型设计.
    """
    key: ClassVar[str]

    @classmethod
    def read(cls, message: "Message") -> Optional["Payload"]:
        value = message.payload.get(cls.key, None)
        if value is None:
            return None
        return cls(**value)

    def set(self, message: "Message") -> None:
        message.payload[self.key] = self.model_dump()


class Attachment(BaseModel, ABC):
    """
    消息上可以追加的附件.
    """
    key: ClassVar[str]

    @classmethod
    def read(cls, message: "Message") -> Optional[List["Attachment"]]:
        value = message.attachments.get(cls.key, None)
        if not value:
            return None
        result = []
        for item in value:
            result.append(cls(**item))
        return result

    def add(self, message: "Message") -> None:
        values = message.attachments.get(self.key)
        if values is None:
            values = []
        values.append(self.model_dump())
        message.attachments[self.key] = values


class Message(BaseModel):
    """
    消息体的容器. 通用的抽象设计.
    可以是一个完整的消息, 也可以是一个包. 通过 pack 字段来做区分.
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

    callers: List[Caller] = Field(default_factory=list, description="将 callers 作为一种单独的类型. ")

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

    def buff(self, pack: "Message") -> Optional["Message"]:
        """
        :param pack:
        :return: 如果 buff 成功, 返回一个当前 buff 的 message. 如果 buff 失败, 则返回 None.
        """
        if pack.get_type() != self.get_type():
            return None
        if pack.msg_id and self.msg_id and pack.msg_id != self.msg_id:
            return None
        if not pack.pack:
            return pack
        self.update(pack)
        return self

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
        if pack.callers:
            self.callers.extend(pack.callers)

    def get_type(self) -> str:
        return self.type or DefaultTypes.DEFAULT

    def dump(self) -> Dict:
        return self.model_dump(exclude_defaults=True)


class MessageClass(ABC):
    """
    一种特殊的 Message, 本体是别的数据结构, 但可以通过 to_messages 方法生成一条或多条消息.
    """

    def to_messages(self) -> Iterable[Message]:
        pass


MessageType = Union[Message, MessageClass, str]
"""将三种类型的数据统一视作 message 类型. """


class MessageTypeParser:
    """
    处理 MessageType
    """

    def __init__(self, role: str = Role.ASSISTANT.value) -> None:
        self.role = role

    def parse(self, messages: Iterable[MessageType]) -> Iterable[Message]:
        for item in messages:
            if isinstance(item, Message):
                yield item
            if isinstance(item, MessageClass):
                yield from item.to_messages()
            if isinstance(item, str):
                yield Message.new(content=item, role=self.role)
            else:
                # todo: 需要日志?
                pass

    def unknown(self, item) -> None:
        """
        unknown 消息类型的处理逻辑.
        默认忽视, 可以重写这个方法.
        """
        return
