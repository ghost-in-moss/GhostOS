import enum
import time
from typing import Optional, Dict, Set, Iterable, Union, List, ClassVar
from typing_extensions import Self
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from ghostos.helpers import uuid

__all__ = [
    "Message", "Role", "DefaultMessageTypes",
    "MessageClass",
    "MessageKind", "MessageKindParser",
    "Payload", "PayloadItem", "Attachment", "Caller",
]


class Role(str, enum.Enum):
    """
    消息体的角色, 对齐了 OpenAI
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"
    TOOL = "tool"

    @classmethod
    def all(cls) -> Set[str]:
        return set(map(lambda x: x.value, cls))

    @classmethod
    def new_assistant_system(
            cls,
            content: str,
            memory: Optional[str] = None,
    ):
        return cls.ASSISTANT.new(content, memory=memory, name="__system__")

    def new(
            self,
            content: str,
            memory: Optional[str] = None,
            name: Optional[str] = None,
            type_: Optional[str] = None,
    ) -> "Message":
        return Message.new_tail(
            type_=type_ if type_ else DefaultMessageTypes.DEFAULT.value,
            role=self.value,
            name=name,
            content=content,
            memory=memory,
        )


class DefaultMessageTypes(str, enum.Enum):
    DEFAULT = ""
    CHAT_COMPLETION = "openai.chat_completion"
    ERROR = "ghostos.messages.error"
    FINAL = "ghostos.messages.final"

    def new(
            self, *,
            content: str, role: str = Role.ASSISTANT.value, memory: Optional[str] = None, name: Optional[str] = None,
    ) -> "Message":
        chunk = not self.is_protocol_type(self.value)
        return Message(content=content, memory=memory, name=name, type=self.value, role=role, chunk=chunk)

    def new_assistant(
            self, *,
            content: str, memory: Optional[str] = None, name: Optional[str] = None,
    ):
        return self.new(content=content, role=Role.ASSISTANT.value, memory=memory, name=name)

    def new_system(
            self, *,
            content: str,
            memory: Optional[str] = None,
            msg_id: Optional[str] = None,
    ):
        data = dict(content=content, role=Role.SYSTEM.value, memory=memory)
        if msg_id is not None:
            data['msg_id'] = msg_id
        return self.new(**data)

    def new_user(
            self, *,
            content: str, memory: Optional[str] = None, name: Optional[str] = None,
    ):
        return self.new(content=content, role=Role.USER.value, memory=memory, name=name)

    def match(self, message: "Message") -> bool:
        return message.type == self.value

    @classmethod
    def final(cls):
        return Message(type=cls.FINAL.value, role=Role.ASSISTANT.value, chunk=False)

    @classmethod
    def is_final(cls, pack: "Message") -> bool:
        return pack.type == cls.FINAL.value

    @classmethod
    def is_protocol_message(cls, message: "Message") -> bool:
        return cls.is_protocol_type(message.type)

    @classmethod
    def is_protocol_type(cls, value: str) -> bool:
        return value in {cls.ERROR, cls.FINAL}


class Caller(BaseModel):
    """
    消息协议中用来描述一个工具或者function 的调用请求.
    """
    id: Optional[str] = Field(default=None, description="caller 的 id, 用来 match openai 的 tool call 协议. ")
    name: str = Field(description="方法的名字.")
    arguments: str = Field(description="方法的参数. ")
    functional_token: bool = Field(default=False, description="caller 是否是基于协议生成的?")

    def add(self, message: "Message") -> None:
        message.callers.append(self)


class Payload(BaseModel, ABC):
    """
    消息体的可扩展的部分. 拥有强类型设计.
    """
    key: ClassVar[str]

    @classmethod
    def read(cls, message: "Message") -> Optional["Payload"]:
        value = message.payloads.get(cls.key, None)
        if value is None:
            return None
        return cls(**value)

    def set(self, message: "Message") -> None:
        message.payloads[self.key] = self.model_dump()

    def exists(self, message: "Message") -> bool:
        return self.key in message.payloads


class PayloadItem(Payload, ABC):
    """
    自身可以粘包的特殊 payload.
    比如 tokens 的计数.
    """

    @abstractmethod
    def join(self, payload: "PayloadItem") -> "PayloadItem":
        pass

    def set(self, message: "Message") -> None:
        exists = message.payloads.get(self.key, None)
        if exists is not None:
            join = self.__class__(**exists)
            payload = self.join(join)
            payload.set(message)
            return
        super().set(message)


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


# the Message class is a container for every kind of message and it's chunks.
# I need this container because:
# 1. I hate weak-type container of message, countless type checking and adapting
# 2. I have not found a community-accepted message protocol for Ai Model messages.
# So I developed this wheel, may be a bad move, but happy to replace it with a mature library someday.
#
# 这个消息类是各种消息类型的一个通用容器.
# 我需要一个这样的容器是因为:
# 1. 讨厌弱类型消息, 需要做无数的校验和适配, 缺乏规则. 比如 OpenAI 的那个极其复杂的 dict.
# 2. 我没找到一个社区广泛使用的标准消息协议.
# 所以重复造了这个轮子, 如果未来发现了成熟的库, 要果断取代掉它. 为此全链路对 Message 的依赖要控制好.
# 把 Message 用于创建消息的地方, 很难修改. 但它作为传输时的 item, 是可以替代的.
#
# the basic logic of this container:
# 1. Message instance could be a complete message, or a chunk.
# 2. I can parse Message to dict/json/serialized data, and unpack a Message from them.
#    the complete Message instance must have msg_id for tracking, but the chunk does not.
# 3. I need a message has a default protocol to show it to User/Agent differently.
#    so this container has two field, content(to user) and memory (to llm).
# 4. the basic information of message are strong typed, but dynamic payloads or attachments have a certain way to parse.
# 5. both client side and server side can define it own parser with message type.
# 6. each type of message can either be parsed to LLM Message (like OpenAI Message), or ignore.
# 7. define a common action caller for LLM, compatible for JSONSchema Tool, function call or FunctionalTokens.
# 8. the streaming chunks always have a head package (introduce following chunks),
#    and a tail package (the complete message).
#
# 基本设计逻辑:
# 1. Message 既可以是一个完整的消息, 也可以是一个间包. 它们通常有相同的结构.
# 2. 可以用 dict/json/别的序列化协议 传输它, 也可以从这些协议反解. 因此用了 pydantic.
#    完整的消息体必须有 msg_id, 但中间包不需要它.
# 3. 消息对客户端和 AI 模型的展示方式可以不一样. 所以有 content 和 memory 字段的区分.
# 4. 消息的基础信息是强类型的, 那些动态类型的信息可以通过确定的方式反解.
# 5. 客户端和服务端可以根据需要, 定义自己的消息转义协议.
# 6. 所有的完整消息要么能被解析成模型的消息, 要么就应该忽略它. 避免展示加工不了的.
# 7. 用一个 caller 兼容各种模型的 action caller.
# 8. 流式传输的消息包, 应该有 首包 / 间包 / 尾包. 尾包是一个粘包后的完整包.
class Message(BaseModel):
    """ message protocol """

    msg_id: str = Field(default="", description="unique message id. ")
    ref_id: Optional[str] = Field(default=None, description="the referenced message id.")
    type: str = Field(default="", description="default message type, if empty, means text")
    created: float = Field(
        default=0.0,
        description="Message creation time, only available in head chunk or complete one",
    )
    chunk: bool = Field(default=True, description="if the message is a chunk or a complete one")

    role: str = Field(default=Role.ASSISTANT.value, description="Message role", enum=Role.all())
    name: Optional[str] = Field(default=None, description="Message sender name")

    content: Optional[str] = Field(
        default=None,
        description="Message content that for client side. empty means it shall not be showed",
    )
    memory: Optional[str] = Field(
        default=None,
        description="Message memory that for llm, if none, means content is memory",
    )

    # --- attachments --- #

    payloads: Dict[str, Dict] = Field(
        default_factory=dict,
        description="payload type key to payload item. payload shall be a strong-typed dict"
    )
    attachments: Dict[str, List[Dict]] = Field(
        default_factory=dict,
        description="attachment type key to attachment items. attachment shall be a strong-typed dict",
    )

    callers: List[Caller] = Field(
        default_factory=list,
        description="the callers parsed in a complete message."
    )

    chunk_count: int = Field(default=0, description="how many chunks of this complete message")
    time_cast: float = Field(default=0.0, description="from first chunk to tail message.")

    streaming_id: Optional[str] = Field(
        default=None,
        description="may be multiple streaming exists, use streaming id to separate them into a order",
    )

    @classmethod
    def new_head(
            cls, *,
            role: str = Role.ASSISTANT.value,
            typ_: str = "",
            content: Optional[str] = None,
            memory: Optional[str] = None,
            name: Optional[str] = None,
            msg_id: Optional[str] = None,
            ref_id: Optional[str] = None,
            created: int = 0,
    ):
        """
        create a head chunk message
        :param role:
        :param typ_:
        :param content:
        :param memory:
        :param name:
        :param msg_id:
        :param ref_id:
        :param created:
        :return:
        """
        if msg_id is None:
            msg_id = uuid()
        if created <= 0:
            created = round(time.time(), 4)
        return cls(
            role=role, name=name, content=content, memory=memory, chunk=True,
            type=typ_,
            ref_id=ref_id,
            msg_id=msg_id, created=created,
        )

    @classmethod
    def new_tail(
            cls, *,
            type_: str = "",
            role: str = Role.ASSISTANT.value,
            content: Optional[str] = None,
            memory: Optional[str] = None,
            name: Optional[str] = None,
            msg_id: Optional[str] = None,
            ref_id: Optional[str] = None,
            created: int = 0,
    ):
        """
        create a tail message, is the complete message of chunks.
        :param type_:
        :param role:
        :param content:
        :param memory:
        :param name:
        :param msg_id:
        :param ref_id:
        :param created:
        :return:
        """
        msg = cls.new_head(
            role=role, name=name, content=content, memory=memory,
            typ_=type_,
            msg_id=msg_id,
            ref_id=ref_id,
            created=created,
        )
        msg.chunk = False
        return msg

    @classmethod
    def new_chunk(
            cls, *,
            typ_: str = "",
            role: str = Role.ASSISTANT.value,
            content: Optional[str] = None,
            memory: Optional[str] = None,
            name: Optional[str] = None,
    ):
        """
        create a chunk message.
        :param typ_:
        :param role:
        :param content:
        :param memory:
        :param name:
        :return:
        """
        return cls(
            role=role, name=name, content=content, memory=memory, chunk=True,
            type=typ_,
        )

    def get_content(self) -> str:
        """
        get content of this message that is showed to model
        if result is empty, means do not show it to model.
        """
        if self.memory is None:
            return self.content if self.content else ""
        return self.memory

    def patch(self, chunk: "Message") -> Optional["Message"]:
        """
        patch a chunk to the current message until get a tail message or other message's chunk
        :param chunk: the chunk to patch.
        :return: if patch succeeds, return the patched message. None means it is other message's chunk
        """
        # if the type is not same, it can't be patched
        pack_type = chunk.get_type()
        if pack_type and pack_type != self.get_type():
            return None
        # the chunk message shall have the same message id or empty one
        if chunk.msg_id and self.msg_id and chunk.msg_id != self.msg_id:
            return None
        # if not a chunk, just return the tail message.
        # tail message may be changed by outside method such as moderation.
        if not chunk.chunk:
            return chunk.model_copy()
        # otherwise, update current one.
        self.update(chunk)
        # add msg_id to each chunk
        chunk.msg_id = self.msg_id
        return self

    def as_head(self) -> Self:
        item = self.model_copy(deep=True)
        if not item.msg_id:
            item.msg_id = uuid()
        if not self.created:
            item.created = time.time()
        return item

    def as_tail(self) -> Self:
        item = self.as_head()
        item.chunk = False
        return item

    def get_copy(self) -> "Message":
        """
        :return: deep copy
        """
        return self.model_copy(deep=True)

    def update(self, pack: "Message") -> None:
        """
        update the fields.
        do not call this method outside patch unless you know what you are doing
        """
        if not self.msg_id:
            # 当前消息的 msg id 不会变更.
            self.msg_id = pack.msg_id
        if not self.type:
            # type 也不会变更.
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

        self.payloads.update(pack.payloads)

        if pack.attachments is not None:
            for key, items in pack.attachments.items():
                saved = self.attachments.get(key, [])
                saved.append(*items)
                self.attachments[key] = saved
        if pack.callers:
            self.callers.extend(pack.callers)
        self.chunk_count += 1
        if self.created:
            now = round(time.time(), 4)
            self.time_cast = round(now - self.created, 4)

    def get_type(self) -> str:
        """
        return a message type
        """
        return self.type or DefaultMessageTypes.DEFAULT

    def is_empty(self) -> bool:
        """
        a message is empty means it has no content, payloads, callers, or attachments
        """
        no_content = not self.content and not self.memory
        no_payloads = not self.payloads and not self.attachments and not self.callers
        return no_content and no_payloads

    def is_complete(self) -> bool:
        """
        complete message is not a chunk one
        """
        return not self.chunk

    def dump(self) -> Dict:
        """
        dump a message dict without default value.
        """
        return self.model_dump(exclude_defaults=True)


class MessageClass(ABC):
    """
    A message class with every field that is strong-typed
    the payloads and attachments shall parse to dict when generate to a Message.
    """

    @abstractmethod
    def to_message(self) -> Message:
        pass

    @classmethod
    @abstractmethod
    def from_message(cls, container: Message) -> Optional[Self]:
        """
        from a message container generate a strong-typed one.
        :param container:
        :return: None means type not match.
        """
        pass


MessageKind = Union[Message, MessageClass, str]
"""sometimes we need three forms of the message to define an argument or property."""


class MessageKindParser:
    """
    middleware that parse weak MessageKind into Message chunks
    """

    def __init__(self, role: str = Role.ASSISTANT.value, ref_id: Optional[str] = None) -> None:
        self.role = role
        self.ref_id = ref_id

    def parse(self, messages: Iterable[MessageKind]) -> Iterable[Message]:
        for item in messages:
            if isinstance(item, Message):
                yield self._with_ref(item)
            if isinstance(item, MessageClass):
                msg = item.to_message()
                yield self._with_ref(msg)
            if isinstance(item, str):
                if not item:
                    # exclude empty message
                    continue
                msg = Message.new_tail(content=item, role=self.role)
                yield self._with_ref(msg)
            else:
                # todo: 需要日志?
                pass

    def _with_ref(self, item: Message) -> Message:
        if self.ref_id is not None:
            item.ref_id = self.ref_id
        return item
