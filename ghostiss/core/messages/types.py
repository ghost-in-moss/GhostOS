import enum
import json
from typing import List, Type, Optional, Dict, ClassVar, TypedDict, Iterable
from pydantic import BaseModel, Field
from ghostiss.core.messages.message import Message, Role, Header
from ghostiss.core.messages.openai import (
    ChatCompletionMessage,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionFunctionMessageParam,
    OPENAI_MESSAGE_TYPES,
)

__all__ = [
    "DefaultTypes",
    "TextMsg", "AIMsg", "FuncResp",
    "MessageTypesLoader",
]


class DefaultTypes(str, enum.Enum):

    # 文本类型的消息.
    TEXT = "text"
    """标准的文本类型消息"""

    # DEBUG = "debug"
    # """端上不应该展示的消息. 本质上仍然是文本. """

    # VARIABLE = "variable"
    # """变量类型的消息. 需要作为 llm 可以理解的变量, 同时对端上展示一个结构化的 json. """

    CHAT_COMPLETION = "chat_completion"

    MULTI_FUNC_CALL = "multi_func_call"

    FUNC_RESP = "func_resp"
    """caller 的返回值. """

    IMAGES = "images"
    """对齐 gpt 多模态的 images 类型"""


# --- methods --- #


def new_openai_text(role: str, content: str, name: Optional[str] = None) -> OPENAI_MESSAGE_TYPES:
    if role == Role.USER:
        return ChatCompletionUserMessageParam(
            content=content, name=name, role="user",
        )
    elif role == Role.SYSTEM:
        return ChatCompletionSystemMessageParam(
            content=content, name=name, role="system",
        )
    elif role == Role.ASSISTANT:
        return ChatCompletionAssistantMessageParam(
            content=content, name=name, role="assistant",
        )
    elif role == Role.FUNCTION:
        return ChatCompletionFunctionMessageParam(
            content=content, name=name, role="function",
        )
    else:
        raise ValueError(f"Unsupported role: {role}")


# ---- messages ---- #

class TextMsg(Message):
    """
    最基础的文本类型的消息.
    """

    msg_type: ClassVar[str] = DefaultTypes.TEXT.value

    content: str = Field(description="Message content")
    memory: Optional[str] = Field(default=None, description="Message memory")

    def as_openai_message(self) -> Iterable[OPENAI_MESSAGE_TYPES]:
        yield new_openai_text(self.role, self.content, self.name)

    def as_openai_memory(self) -> Iterable[OPENAI_MESSAGE_TYPES]:
        content = self.content
        if self.memory is not None:
            content = self.content
        if content:
            yield new_openai_text(self.role, content, self.name)


class AIMsg(Message, ChatCompletionMessage):
    """
    基于 openai chat completion 实现的 ai msg.
    """

    memory: Optional[str] = Field(default=None, description="Message memory")

    def as_openai_chat_completion(self, content: str = None) -> ChatCompletionMessage:
        data = self.model_dump()
        if content:
            data["content"] = content
        return ChatCompletionMessage(**data)

    def as_openai_message(self) -> Iterable[ChatCompletionMessage]:
        # 由于参数一样, 所以可以直接覆盖.
        yield self.as_openai_chat_completion()

    def as_openai_memory(self) -> Optional[ChatCompletionMessage]:
        if self.memory is None:
            yield self.as_openai_chat_completion()
        elif self.memory != "":
            yield self.as_openai_chat_completion(self.memory)


class DefaultToolResult(TypedDict):
    result: dict
    err: Optional[str]


class FuncResp(Message):
    """
    设计一种标准的 function 返回消息体.
    """

    msg_type: ClassVar[str] = DefaultTypes.FUNC_RESP.value
    name: Optional[str] = Field(default=None, description="tool name")
    role: str = Field(const=Role.FUNCTION, description="tool role")

    call_id: str = Field(description="tool call ID")
    memory: Optional[str] = Field(default=None, description="Caller memory")

    result: dict = Field(description="Caller result")
    err: Optional[str] = Field(description="Caller error")

    def as_openai_memory(self) -> Iterable[OPENAI_MESSAGE_TYPES]:
        if self.memory == "":
            return []
        return self.as_openai_message()

    def as_openai_message(self) -> Iterable[OPENAI_MESSAGE_TYPES]:
        content = self.memory
        if not content:
            result = DefaultToolResult(result=self.result, err=self.err)
            content = json.dumps(result)

        if self.id:
            yield ChatCompletionToolMessageParam(
                content=content,
                role="tool",
                tool_call_id=self.call_id,
            )
        elif self.name:
            yield ChatCompletionFunctionMessageParam(
                content=content,
                name=self.name,
                role="function",
            )
        else:
            # 默认使用 dict.
            yield dict(
                content=content,
                role="tool",
                tool_call_id=self.id,
                name=self.name,
            )


# --- loader --- #

class MessageTypesLoader:
    """
    从 dict 中反解出一个完整的 Message 类型. 根据 kind 字段进行判断.
    """

    def __init__(self, types: Optional[List[Type[Message]]] = None) -> None:
        self.types: Dict[str, Type[Message]] = {}
        if types is None:
            types = [TextMsg, AIMsg, FuncResp]
        for typ in types:
            self.types[typ.msg_type] = typ

    def new(self, data: dict, typ: str = "") -> Optional[Message]:
        if not typ:
            typ = data.get("type", "")
        typ = self.types.get(typ, None)
        if typ is None:
            return None
        return typ.new(**data)

    def from_header(self, header: Header) -> Message:
        """
        通过 header 实例化一个消息体.
        """
        typ = header.type
        data = header.model_dump()
        return self.new(data, typ)
