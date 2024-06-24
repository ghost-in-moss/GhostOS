import enum
import json
from typing import List, Type, Optional, Dict, ClassVar, TypedDict, Iterable
from typing_extensions import Literal
from pydantic import BaseModel, Field
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from ghostiss.blueprint.messages.message import Message, Role, FunctionCall, ToolCall, PACK
from ghostiss.entity import EntityFactory, EntityMeta
from ghostiss.blueprint.messages.openai import (
    ChatCompletionMessage,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionFunctionMessageParam,
)

__all__ = [
    "DefaultTypes",
    "TextMsg", "AssistantMsg", "ToolMsg",
]


class DefaultTypes(str, enum.Enum):
    # 文本类型的消息.
    TEXT = "text"
    """标准的文本类型消息"""

    # DEBUG = "debug"
    # """端上不应该展示的消息. 本质上仍然是文本. """

    # VARIABLE = "variable"
    # """变量类型的消息. 需要作为 llm 可以理解的变量, 同时对端上展示一个结构化的 json. """

    ASSISTANT = "assistant"

    TOOL_CALLBACK = "tool_callback"

    IMAGES = "images"
    """对齐 gpt 多模态的 images 类型"""


# --- methods --- #


class TextMsg(Message):
    """
    文本消息.
    """

    type: Literal[DefaultTypes.TEXT]
    content: str = Field(default="", description="Message content")
    memory: Optional[str] = Field(default=None, description="Message as memory")

    def buff(self, pack: PACK) -> bool:
        # 不接受 buff.
        return False

    def as_openai_message(self) -> Iterable[ChatCompletionMessageParam]:
        content = self.content
        if not content:
            return []
        yield new_openai_text(self.role, self.content, self.name)

    def as_openai_memory(self) -> Iterable[ChatCompletionMessageParam]:
        content = self.memory
        if content is None:
            content = self.content
        if not content:
            return []
        yield new_openai_text(self.role, self.content, self.name)


class ToolMsg(Message):
    """
    对齐 openai 的 tool message.
    """

    type: Literal[DefaultTypes.TOOL_CALLBACK]

    content: str
    tool_call_id: str

    role: Literal["tool"]

    def buff(self, pack: PACK) -> bool:
        return False

    def as_openai_message(self) -> Iterable[ChatCompletionMessageParam]:
        """
        理论上不对外展示.
        """
        yield ChatCompletionToolMessageParam(
            content=self.content,
            tool_call_id=self.tool_call_id,
            role=self.role,
        )

    def as_openai_memory(self) -> Iterable[ChatCompletionMessageParam]:
        return self.as_openai_message()


class AssistantMsg(Message):
    """
    对齐 openai 的 chat completion.
    """
    type: ClassVar[str] = DefaultTypes.ASSISTANT
    # --- content --- #

    role: Literal[Role.ASSISTANT]
    content: Optional[str] = Field(default=None, description="Message content")
    memory: Optional[str] = Field(default=None, description="Message as memory")
    reset: bool = False

    # --- function call --- #

    function_call: Optional[FunctionCall] = Field(default=None, description="Function call")
    tool_calls: Optional[List[ToolCall]] = Field(default=None, description="Tool calls")

    def buff(self, pack: PACK) -> bool:
        if isinstance(pack, AssistantMsg):
            return self._buff(pack)

        item = AssistantMsg.new_entity(pack)
        if item is None:
            return False
        return self._buff(item)

    def _buff(self, item: "AssistantMsg") -> bool:
        if self.msg_id and item.msg_id and self.msg_id != item.msg_id:
            return False

        self.msg_id = item.msg_id or self.msg_id

        if item.reset or self.content is None:
            self.content = item.content
        elif item.content is not None:
            self.content += item.content

        if item.reset or item.memory is not None:
            self.memory = item.memory

        if item.reset or item.function_call is not None:
            self.function_call = item.function_call

        if item.reset or self.tool_calls is None:
            self.tool_calls = item.tool_calls
        elif item.tool_calls is not None:
            tools = {}
            for tool_call in self.tool_calls:
                tools[tool_call.name] = tool_call
            for tool_call in item.tool_calls:
                tools[tool_call.name] = tool_call
            self.tool_calls = list(tools.values())

        if item.reset or self.attachments is None:
            self.attachments = item.attachments
        elif item.attachments is not None:
            self.attachments.update(item.attachments)

    def as_openai_message(self) -> Iterable[ChatCompletionMessageParam]:
        data = self.model_dump(include={"role", "content", "function_call", "tool_calls"})
        yield ChatCompletionAssistantMessageParam(**data)

    def as_openai_memory(self) -> Iterable[ChatCompletionMessageParam]:
        content = self.content
        if self.memory is not None:
            content = self.memory
        if not content:
            return []
        data = self.model_dump(include={"role", "function_call", "tool_calls"})
        data["content"] = content
        yield ChatCompletionAssistantMessageParam(**data)

    @classmethod
    def new_pack_from_openai(cls, pack: ChatCompletionMessage) -> "AssistantMsg":
        return cls(**pack.model_dump())


def new_openai_text(role: str, content: str, name: Optional[str] = None) -> ChatCompletionMessageParam:
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


# # ---- messages ---- #
#
# class TextMsg(Message):
#     """
#     最基础的文本类型的消息.
#     """
#
#     msg_type: ClassVar[str] = DefaultTypes.TEXT.value
#
#     content: str = Field(description="Message content")
#     memory: Optional[str] = Field(default=None, description="Message memory")
#
#     def as_openai_message(self) -> Iterable[ChatCompletionMessageParam]:
#         yield new_openai_text(self.role, self.content, self.name)
#
#     def as_openai_memory(self) -> Iterable[ChatCompletionMessageParam]:
#         content = self.content
#         if self.memory is not None:
#             content = self.content
#         if content:
#             yield new_openai_text(self.role, content, self.name)
#
#
# class AIMsg(Message, ChatCompletionMessage):
#     """
#     基于 openai chat completion 实现的 ai msg.
#     """
#
#     memory: Optional[str] = Field(default=None, description="Message memory")
#
#     def as_openai_chat_completion(self, content: str = None) -> ChatCompletionMessage:
#         data = self.model_dump()
#         if content:
#             data["content"] = content
#         return ChatCompletionMessage(**data)
#
#     def as_openai_message(self) -> Iterable[ChatCompletionMessage]:
#         # 由于参数一样, 所以可以直接覆盖.
#         yield self.as_openai_chat_completion()
#
#     def as_openai_memory(self) -> Optional[ChatCompletionMessage]:
#         if self.memory is None:
#             yield self.as_openai_chat_completion()
#         elif self.memory != "":
#             yield self.as_openai_chat_completion(self.memory)
#
#
# class DefaultToolResult(TypedDict):
#     result: dict
#     err: Optional[str]


# class FuncResp(Message):
#     """
#     设计一种标准的 function 返回消息体.
#     """
#
#     msg_type: ClassVar[str] = DefaultTypes.FUNC_RESP.value
#     name: Optional[str] = Field(default=None, description="tool name")
#     role: str = Field(const=Role.FUNCTION, description="tool role")
#
#     call_id: str = Field(description="tool call ID")
#     memory: Optional[str] = Field(default=None, description="Caller memory")
#
#     result: dict = Field(description="Caller result")
#     err: Optional[str] = Field(description="Caller error")
#
#     def as_openai_memory(self) -> Iterable[ChatCompletionMessageParam]:
#         if self.memory == "":
#             return []
#         return self.as_openai_message()
#
#     def as_openai_message(self) -> Iterable[ChatCompletionMessageParam]:
#         content = self.memory
#         if not content:
#             result = DefaultToolResult(result=self.result, err=self.err)
#             content = json.dumps(result)
#
#         if self.id:
#             yield ChatCompletionToolMessageParam(
#                 content=content,
#                 role="tool",
#                 tool_call_id=self.call_id,
#             )
#         elif self.name:
#             yield ChatCompletionFunctionMessageParam(
#                 content=content,
#                 name=self.name,
#                 role="function",
#             )
#         else:
#             # 默认使用 dict.
#             yield dict(
#                 content=content,
#                 role="tool",
#                 tool_call_id=self.id,
#                 name=self.name,
#             )


# ---- factory ---- #

class MessageFactory(EntityFactory[Message]):
    """
    用来生成 messages 的.
    """

    def __init__(self, types: Optional[List[Type[Message]]]):
        self._types = {}
        if types is None:
            types = [TextMsg, AssistantMsg, ToolMsg]

        for type_ in types:
            self._types[type_.entity_kind()] = type_

    def new_entity(self, meta_data: EntityMeta) -> Optional[Message]:
        kind = self._types.get(meta_data["type"], None)
        if kind is None:
            return None
        return kind.new_entity(meta_data)
