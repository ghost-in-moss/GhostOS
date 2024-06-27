from abc import ABC, abstractmethod
from typing import ClassVar, Optional, Type, TypeVar, Iterable, List
from ghostiss.blueprint.messages.message import Message, Caller
from openai.types.chat.chat_completion_message import FunctionCall as OpenAIFunctionCall
from pydantic import BaseModel

__all__ = [
    "Payload", "CallerPayload",
    "read_payload", "add_payload", "read_payload_callers",
    "FunctionCall",
]


class Payload(BaseModel, ABC):
    """
    消息体的可扩展详细内容.
    """
    key: ClassVar[str]


class CallerPayload(Payload, ABC):

    @abstractmethod
    def callers(self) -> Iterable[Caller]:
        pass


P = TypeVar("P", bound=Payload)


def read_payload(cls: Type[P], message: Message) -> Optional["P"]:
    value = message.payload.get(cls.key, None)
    if value is None:
        return None
    return cls(**value)


def read_payload_callers(types: List[Type[CallerPayload]], message: Message) -> Iterable[Caller]:
    for typ in types:
        payload = read_payload(typ, message)
        if payload is not None:
            for caller in payload.callers():
                yield caller


def add_payload(payload: Payload, message: Message) -> None:
    message.payload[payload.key] = payload.model_dump()


class FunctionCall(CallerPayload, OpenAIFunctionCall):
    """
    标准的 function call, 基于 openai 的字段设计.
    """
    key: ClassVar[str] = "function_call"

    def callers(self) -> Iterable[Caller]:
        yield Caller(name=self.name, arguments=self.arguments)
