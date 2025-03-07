from __future__ import annotations
import enum
import time
from datetime import datetime
from typing import Optional, Dict, Set, Iterable, Union, List, Any, ClassVar, Type
from typing_extensions import Self, Literal
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from ghostos_common.helpers import uuid
from ghostos_container import Container
from ghostos_common.entity import EntityType
from copy import deepcopy

__all__ = [
    "Message", "Role", "MessageType",
    "MessageStage",
    "MessageClass", "MessageClassesParser",
    "MessageKind",
    "FunctionCaller", "FunctionOutput",
]

SeqType = Literal["head", "chunk", "complete"]


class Role(str, enum.Enum):
    """
    消息体的角色, 对齐了 OpenAI
    """

    UNKNOWN = ""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    DEVELOPER = "developer"

    @classmethod
    def all(cls) -> Set[str]:
        return set(map(lambda x: x.value, cls))

    @classmethod
    def new_system(
            cls,
            content: str,
            memory: Optional[str] = None,
            stage: str = "",
    ):
        # maybe switch to developer role in future.
        return cls.SYSTEM.new(content, memory=memory, stage=stage)

    @classmethod
    def is_system(cls, role: str) -> bool:
        return role == cls.SYSTEM.value or role == cls.DEVELOPER.value

    def new(
            self,
            content: str,
            memory: Optional[str] = None,
            name: Optional[str] = None,
            type_: Optional[str] = None,
            stage: str = "",
            msg_id: Optional[str] = None,
    ) -> "Message":
        return Message.new_tail(
            type_=type_ if type_ else MessageType.DEFAULT.value,
            role=self.value,
            name=name,
            content=content,
            memory=memory,
            stage=stage,
            msg_id=msg_id,
        )


class MessageType(str, enum.Enum):
    DEFAULT = ""
    TEXT = "text"
    VARIABLE = "variable"
    FUNCTION_CALL = "function_call"
    FUNCTION_OUTPUT = "function_output"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    FINAL = "final"

    # system message type
    CONFIRM = "confirm"
    ERROR = "error"
    DEBUG = "debug"

    def new(
            self, *,
            content: str,
            role: str = Role.ASSISTANT.value,
            memory: Optional[str] = None,
            name: Optional[str] = None,
            msg_id: Optional[str] = None,
            call_id: Optional[str] = None,
    ) -> "Message":
        return Message(
            msg_id=msg_id or "",
            content=content, memory=memory, name=name, type=self.value, role=role,
            call_id=call_id,
        ).as_tail(copy=False)

    def new_assistant(
            self,
            *,
            content: str,
            memory: Optional[str] = None,
            name: Optional[str] = None,
            msg_id: Optional[str] = None,
    ):
        return self.new(
            content=content,
            role=Role.ASSISTANT.value,
            memory=memory,
            name=name,
            msg_id=msg_id or None,
        )

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

    @classmethod
    def final(cls):
        return Message(type=cls.FINAL.value, role="").as_tail()

    def match(self, message: "Message") -> bool:
        return message.type == self.value

    @classmethod
    def is_final(cls, pack: "Message") -> bool:
        return pack.type == cls.FINAL.value

    @classmethod
    def is_text(cls, message: Message) -> bool:
        return message.type == cls.TEXT.value or message.type == cls.DEFAULT.value

    @classmethod
    def is_protocol_message(cls, message: Optional["Message"]) -> bool:
        if message is None:
            return True
        return cls.is_protocol_type(message.type)

    @classmethod
    def is_protocol_type(cls, value: str) -> bool:
        return value in {cls.ERROR, cls.FINAL}


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
# todo: openai 的 realtime api 协议比较整齐, 应该考虑用这个思路重构. 需要考虑几点:
# todo: 1. 传输协议和存储协议分开.
# todo: 2. 传输用弱类型.
# todo: 3. delta 用于流式传输, content part 用来解决富文本, item 解决消息体.

class MessageStage(str, enum.Enum):
    DEFAULT = ""
    REASONING = "reasoning"

    @classmethod
    def allow(cls, value: str, stages: Optional[Iterable[str]]) -> bool:
        if stages is None:
            stages = {cls.DEFAULT.value}

        if not stages:
            return False

        if isinstance(stages, set):
            if "*" in stages:
                return True
            return value in stages
        else:
            for val in stages:
                if val == "*" or val == value:
                    return True
        return False


class Message(BaseModel):
    """ message protocol """

    msg_id: str = Field(default="", description="unique message id. ")
    call_id: Optional[str] = Field(default=None, description="the call id message id.")
    index: Optional[int] = Field(default=None, description="the index of the message.")
    type: str = Field(default="", description="default message type, if empty, means text")
    stage: str = Field(default="", description="message stage")
    finish_reason: Optional[str] = Field(default=None, description="message finish reason.")

    role: str = Field(default="", description="Message role", enum=Role.all())
    name: Optional[str] = Field(default=None, description="Message sender name")
    content: Optional[str] = Field(
        default=None,
        description="Message content that for client side. empty means it shall not be showed",
    )

    # todo: remove memory, use stage instead.
    memory: Optional[str] = Field(
        default=None,
        description="Message memory that for llm, if none, means content is memory",
    )

    attrs: Dict[str, Any] = Field(
        default_factory=dict,
        description="the additional attrs for the message type"
    )

    payloads: Dict[str, Dict] = Field(
        default_factory=dict,
        description="payload type key to payload item. payload shall be a strong-typed dict"
    )

    callers: List[FunctionCaller] = Field(
        default_factory=list,
        description="the callers parsed in a complete message."
    )

    # chunk_count: int = Field(default=0, description="how many chunks of this complete message")
    # time_cast: float = Field(default=0.0, description="from first chunk to tail message.")

    seq: SeqType = Field(default="chunk", description="sequence type in streaming")
    created: float = Field(default=0.0, description="time when message was created")

    __attachment__: Optional[Any] = None

    @classmethod
    def new_head(
            cls, *,
            role: str = Role.ASSISTANT.value,
            typ_: str = "",
            content: Optional[str] = None,
            memory: Optional[str] = None,
            name: Optional[str] = None,
            msg_id: Optional[str] = None,
            call_id: Optional[str] = None,
            stage: str = "",
    ):
        """
        create a head chunk message
        :param role:
        :param typ_:
        :param content:
        :param memory:
        :param name:
        :param msg_id:
        :param call_id:
        :param stage:
        # :param created:
        :return:
        """
        if msg_id is None:
            msg_id = uuid()
        created = round(time.time(), 3)
        if isinstance(role, Role):
            role = role.value
        if isinstance(typ_, MessageType):
            typ_ = typ_.value
        item = cls(
            role=role,
            name=name,
            content=content,
            memory=memory,
            seq="head",
            type=typ_,
            call_id=call_id,
            msg_id=msg_id,
            stage=stage,
            created=created,
        )
        return item

    @classmethod
    def new_tail(
            cls, *,
            type_: str = "",
            role: str = Role.ASSISTANT.value,
            content: Optional[str] = None,
            memory: Optional[str] = None,
            name: Optional[str] = None,
            msg_id: Optional[str] = None,
            # todo: change to call id
            call_id: Optional[str] = None,
            attrs: Optional[Dict[str, Any]] = None,
            stage: str = "",
    ):
        """
        create a tail message, is the complete message of chunks.
        :param type_:
        :param role:
        :param content:
        :param memory:
        :param name:
        :param msg_id:
        :param call_id:
        :param attrs:
        :param stage:
        :return:
        """
        msg = cls.new_head(
            role=role,
            name=name,
            content=content,
            memory=memory,
            typ_=type_,
            msg_id=msg_id,
            call_id=call_id,
            stage=stage,
        )
        msg.seq = "complete"
        if attrs is None:
            attrs = {}
        msg.attrs = attrs
        return msg

    @classmethod
    def new_chunk(
            cls, *,
            typ_: str = "",
            role: str = Role.ASSISTANT.value,
            content: Optional[str] = None,
            memory: Optional[str] = None,
            name: Optional[str] = None,
            call_id: Optional[str] = None,
            msg_id: Optional[str] = None,
            stage: str = "",
    ):
        """
        create a chunk message.
        :return:
        """
        return cls(
            role=role, name=name, content=content, memory=memory,
            type=typ_,
            call_id=call_id,
            msg_id=msg_id or "",
            seq="chunk",
            stage=stage,
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
        if pack_type and pack_type != self.type:
            is_text = pack_type == MessageType.TEXT.value and not self.type
            if not is_text:
                return None
        # the chunk message shall have the same message id or empty one
        if chunk.msg_id and self.msg_id and chunk.msg_id != self.msg_id:
            return None
        # if not a chunk, just return the tail message.
        # tail message may be changed by outside method such as moderation.
        if chunk.is_complete():
            return chunk.model_copy()
        # otherwise, update current one.
        self.update(chunk)
        # add msg_id to each chunk
        chunk.msg_id = self.msg_id
        return self

    def as_head(self, copy: bool = True) -> Self:
        if copy:
            item = self.get_copy()
        else:
            item = self
        if not item.msg_id:
            item.msg_id = uuid()
        if not self.created:
            item.created = round(time.time(), 3)
        if item.seq == "chunk":
            item.seq = "head"
        return item

    def get_copy(self) -> Self:
        return self.model_copy(deep=True)

    def as_tail(self, copy: bool = True) -> Self:
        item = self.as_head(copy)
        item.seq = "complete"
        return item

    def get_unique_id(self) -> str:
        return f"{self.type}:{self.role}:{self.name}:{self.stage}:{self.msg_id}"

    def update(self, pack: "Message") -> None:
        """
        update the fields.
        do not call this method outside patch unless you know what you are doing
        """
        if not self.msg_id:
            # 当前消息的 msg id 不会变更.
            self.msg_id = pack.msg_id
        if not self.call_id:
            self.call_id = pack.call_id
        if not self.type:
            # only update when self type is empty (default)
            self.type = pack.type
        if pack.stage:
            self.stage = pack.stage

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

        if pack.attrs:
            self.attrs.update(pack.attrs)

        self.payloads.update(deepcopy(pack.payloads))
        if pack.callers:
            self.callers.extend(pack.callers)

    def get_type(self) -> str:
        """
        return a message type
        """
        return self.type or MessageType.DEFAULT

    def is_empty(self) -> bool:
        """
        a message is empty means it has no content, payloads, callers, or attachments
        """
        no_content = not self.content and not self.memory
        no_attrs = not self.attrs
        no_payloads = not self.payloads and self.__attachment__ is None and not self.callers
        return no_content and no_attrs and no_payloads

    def is_complete(self) -> bool:
        """
        complete message is not a chunk one
        """
        return self.seq == "complete" or MessageType.is_protocol_type(self.type)

    def is_head(self) -> bool:
        return self.seq == "head"

    def is_chunk(self) -> bool:
        return self.seq == "chunk"

    def get_seq(self) -> SeqType:
        return self.seq

    def dump(self) -> Dict:
        """
        dump a message dict without default value.
        """
        return self.model_dump(exclude_defaults=True)

    def get_created(self) -> datetime:
        return datetime.fromtimestamp(self.created)

    def __str__(self):
        return self.__repr__()


class MessageClass(BaseModel, ABC):
    """
    A message class with every field that is strong-typed
    the payloads and attachments shall parse to dict when generate to a Message.
    """
    __message_type__: ClassVar[Union[MessageType, str]]

    msg_id: str = Field(default="")
    payloads: Dict[str, Dict] = Field(default_factory=dict)
    role: str = Field(default="")
    stage: str = Field(default="")
    name: Optional[str] = Field(None)

    def to_message(self) -> Message:
        message = Message.new_tail(
            type_=self.__message_type__,
            msg_id=self.msg_id,
            role=self.role,
            stage=self.stage,
            name=self.name,
        )
        message.payloads = self.payloads
        return self._to_message(message)

    @abstractmethod
    def _to_message(self, message: Message) -> Message:
        pass

    @classmethod
    def from_message(cls, message: Message) -> Optional[Self]:
        """
        from a message container generate a strong-typed one.
        :param message:
        :return: None means type not match.
        """
        if not message.is_complete():
            return None

        built = cls._from_message(message)
        if built is None:
            return None
        built.msg_id = message.msg_id
        built.payloads = message.payloads
        built.role = message.role
        built.stage = message.stage
        built.name = message.name
        return built

    @classmethod
    @abstractmethod
    def _from_message(cls, message: Message) -> Optional[Self]:
        pass

    @abstractmethod
    def to_openai_param(self, container: Optional[Container], compatible: bool = False) -> List[Dict]:
        pass


class FunctionCaller(BaseModel):
    """
    消息协议中用来描述一个工具或者function 的调用请求.
    """
    call_id: Optional[str] = Field(default=None, description="caller 的 id, 用来 match openai 的 tool call 协议. ")
    name: str = Field(description="方法的名字.")
    arguments: str = Field(description="方法的参数. ")

    # deprecated
    functional_token: bool = Field(default=False, description="caller 是否是基于协议生成的?")

    def add(self, message: "Message") -> None:
        message.callers.append(self)

    def new_output(self, output: str) -> FunctionOutput:
        return FunctionOutput(
            call_id=self.call_id,
            name=self.name,
            content=output,
        )

    @classmethod
    def from_message(cls, message: Message) -> Iterable[FunctionCaller]:
        if not message.is_complete():
            yield from []
            return
        if message.type == MessageType.FUNCTION_CALL.value:
            yield FunctionCaller(
                call_id=message.call_id,
                name=message.name,
                arguments=message.content,
            )
        if message.callers:
            yield from message.callers


# todo: history code, optimize later
class FunctionOutput(MessageClass):
    __message_type__ = MessageType.FUNCTION_OUTPUT.value

    call_id: Optional[str] = Field(None, description="caller id")
    name: Optional[str] = Field(
        default=None,
        description="caller name, caller id and caller name can not both be empty",
    )
    content: Optional[str] = Field(description="caller output")

    def _to_message(self, message: Message) -> Message:
        message.name = self.name
        message.call_id = self.call_id
        message.content = self.content
        return message

    @classmethod
    def _from_message(cls, message: Message) -> Optional[Self]:
        if message.type != MessageType.FUNCTION_OUTPUT.value:
            return None
        return cls(
            msg_id=message.msg_id,
            call_id=message.call_id,
            name=message.name,
            content=message.content,
            payloads=message.payloads,
        )

    def to_openai_param(self, container: Optional[Container], compatible: bool = False) -> List[Dict]:
        from openai.types.chat.chat_completion_tool_message_param import ChatCompletionToolMessageParam
        from openai.types.chat.chat_completion_function_message_param import ChatCompletionFunctionMessageParam
        if self.call_id:
            return [ChatCompletionToolMessageParam(
                content=self.content,
                role="tool",
                tool_call_id=self.call_id,
            )]
        else:
            return [ChatCompletionFunctionMessageParam(
                content=self.content,
                name=self.name,
                role="function",
            )]


class MessageClassesParser:
    def __init__(
            self,
            classes: Iterable[Type[MessageClass]],
    ) -> None:
        self.classes = {str(cls.__message_type__): cls for cls in classes}

    def parse(self, message: Message) -> Optional[MessageClass]:
        if not message.is_complete():
            return None
        if message.type not in self.classes:
            return None
        cls = self.classes[message.type]
        item = cls.from_message(message)
        return item

    def to_openai_params(
            self,
            message: Message,
            container: Optional[Container],
            compatible: bool = False,
    ) -> Optional[List[Dict]]:
        parsed = self.parse(message)
        if parsed is None:
            return None
        return parsed.to_openai_param(container, compatible)


MessageKind = Union[Message, MessageClass, str, EntityType]
"""sometimes we need three forms of the message to define an argument or property."""
