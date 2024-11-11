from typing import Optional, Dict
from typing_extensions import Self

from .message import Message, MessageClass, MessageType
from pydantic import BaseModel, Field


class DefaultMsgCls(MessageClass):
    message_type = MessageType.DEFAULT
    message: Message

    def __init__(self, message: Message):
        self.message = message

    def to_message(self) -> Message:
        return self.message

    @classmethod
    def from_message(cls, container: Message) -> Optional[Self]:
        if container.is_complete():
            return cls(container)
        return None

    def to_openai_param(self) -> Dict:
        raise NotImplementedError("todo")


class VariableMsgCls(MessageClass, BaseModel):
    """
    变量类型消息.
    """
    message_type: MessageType.VARIABLE

    role: str = Field(default="", description="who send the message")
    name: Optional[str] = Field(None, description="who send the message")
    vid: str = Field(description="variable unique id")
    type: str = Field(description="variable type, used to unmarshal the variable. could be any str, or import path")
    description: str = Field("", description="Description of the variable")

    def to_message(self) -> Message:
        return Message.new_tail(
            type_=MessageType.VARIABLE.value,
            content="",
            role=self.role,
            name=self.name,
            attrs=self.model_dump(include={"vid", "type", "description"})
        )

    @classmethod
    def from_message(cls, container: Message) -> Optional[Self]:
        if container.type != MessageType.VARIABLE.value:
            return None

        data = container.attrs
        if data is None:
            return None
        data["name"] = container.name
        data["role"] = container.role
        obj = cls(**data)
        return obj

    def to_openai_param(self) -> Dict:
        pass
