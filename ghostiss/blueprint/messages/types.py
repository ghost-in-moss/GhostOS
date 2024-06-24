import enum
from typing import List, Type, Optional, ClassVar, Iterable
from typing_extensions import Literal
from pydantic import Field
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_tool_message_param import ChatCompletionToolMessageParam
from openai.types.chat.chat_completion_assistant_message_param import ChatCompletionAssistantMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_function_message_param import ChatCompletionFunctionMessageParam

from ghostiss.blueprint.messages.message import Message, Role, FunctionCall, ToolCall, PACK, Final
from ghostiss.entity import EntityFactory, EntityMeta

__all__ = [
    "DefaultTypes",
    "TextMsg", "AssistantMsg", "ToolMsg",
    "MessageFactory",
]


class DefaultTypes(str, enum.Enum):
    # 文本类型的消息.
    TEXT = "ghostiss.messages.text"
    """标准的文本类型消息"""

    # DEBUG = "debug"
    # """端上不应该展示的消息. 本质上仍然是文本. """

    # VARIABLE = "variable"
    # """变量类型的消息. 需要作为 llm 可以理解的变量, 同时对端上展示一个结构化的 json. """

    ASSISTANT = "ghostiss.messages.assistant"

    TOOL = "ghostiss.messages.tool"

    FINAL = Final.type

    IMAGES = "images"
    """对齐 gpt 多模态的 images 类型"""


# --- methods --- #


class TextMsg(Message):
    """
    文本消息.
    """

    type: ClassVar[str] = DefaultTypes.TEXT
    content: str = Field(default="", description="Message content")
    memory: Optional[str] = Field(default=None, description="Message as memory")

    @classmethod
    def new(cls, *, role: str, content: str, memory: Optional[str] = None) -> "TextMsg":
        return cls(role=role, content=content, memory=memory)

    def buff(self, pack: PACK) -> bool:
        # 不接受 buff.
        return False

    def as_openai_message(self) -> Iterable[ChatCompletionAssistantMessageParam]:
        content = self.content
        if not content:
            return []
        yield new_openai_text(self.role, self.content, self.name)

    def as_openai_memory(self) -> Iterable[ChatCompletionAssistantMessageParam]:
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

    type: ClassVar[str] = DefaultTypes.TOOL

    content: str = Field(default="", description="tool content")
    tool_call_id: str = Field()

    role: Literal["tool"] = "tool"

    @classmethod
    def new(cls, *, content: str, tool_call_id: str) -> "ToolMsg":
        return cls(content=content, tool_call_id=tool_call_id)

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

    role: Literal[Role.ASSISTANT] = Role.ASSISTANT
    content: Optional[str] = Field(default=None, description="Message content")
    memory: Optional[str] = Field(default=None, description="Message as memory")
    reset: bool = False

    # --- function call --- #

    function_call: Optional[FunctionCall] = Field(default=None, description="Function call")
    tool_calls: Optional[List[ToolCall]] = Field(default=None, description="Tool calls")

    @classmethod
    def new(
            cls, *,
            content: Optional[str] = None,
            memory: Optional[str] = None,
            function_call: Optional[FunctionCall] = None,
            tool_calls: Optional[List[ToolCall]] = None,
            reset: bool = False,
    ) -> "AssistantMsg":
        return cls(content=content, memory=memory, function_call=function_call, tool_calls=tool_calls, reset=reset)

    def buff(self, pack: PACK) -> bool:
        if isinstance(pack, AssistantMsg):
            return self._buff(pack)
        elif isinstance(pack, Message):
            return False

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
        return True

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


# ---- factory ---- #

class MessageFactory(EntityFactory[Message]):
    """
    用来生成 messages 的.
    """

    def __init__(self, *, default_type: Optional[Type[Message]] = None, types: Optional[List[Type[Message]]] = None):
        """
        注册各种消息类型.
        """
        self._types = {}
        if types is None:
            # 默认的 types
            types = [TextMsg, AssistantMsg, ToolMsg, Final]

        for type_ in types:
            # 注册 types.
            self._types[type_.entity_type()] = type_
        if default_type is None:
            default_type = TextMsg
        self._default_type = default_type

    def new_entity(self, meta_data: EntityMeta) -> Optional[Message]:
        kind = self._types.get(meta_data["type"], None)
        if kind is None:
            try:
                return self._default_type.new_entity(meta_data)
            except ValueError:
                return None

        return kind.new_entity(meta_data)
