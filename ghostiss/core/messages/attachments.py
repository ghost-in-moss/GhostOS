from abc import ABC, abstractmethod
from typing import ClassVar, Optional, List, TypeVar, Type, Iterable
from pydantic import BaseModel
from ghostiss.core.messages.message import Message, Caller
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall as OpenAIToolCall

__all__ = [
    "Attachment", "CallerAttachment",
    "read_attachments", "add_attachment", "read_attachment_callers",
    "ToolCall",
]


class Attachment(BaseModel, ABC):
    key: ClassVar[str]


class CallerAttachment(Attachment, ABC):

    @abstractmethod
    def callers(self) -> Iterable[Caller]:
        pass


A = TypeVar("A", bound=Attachment)


def read_attachments(cls: Type[A], message: Message) -> Optional[List["A"]]:
    value = message.attachments.get(cls.key, None)
    if not value:
        return None
    result = []
    for item in value:
        result.append(cls(**item))
    return result


def read_attachment_callers(types: List[Type[CallerAttachment]], message: Message) -> Iterable[Caller]:
    for typ in types:
        read = read_attachments(typ, message)
        if read:
            for item in read:
                for caller in item.callers():
                    yield caller


def add_attachment(attachment: Attachment, message: Message) -> None:
    values = message.attachments.get(attachment.key)
    if values is None:
        values = []
    values.append(attachment.model_dump())
    message.attachments[attachment.key] = values


class ToolCall(CallerAttachment, OpenAIToolCall):
    """
    标准的 tools call, 基于 openai 的字段设计.
    """
    key: ClassVar[str] = "tools_call"

    def callers(self) -> Iterable[Caller]:
        yield Caller(id=self.id, name=self.function.name, arguments=self.function.arguments)
