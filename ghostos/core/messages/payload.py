from typing import ClassVar, Optional, Protocol, Dict, Union, Self
from abc import ABC
from pydantic import BaseModel
from .message import Message


class HasPayloads(Protocol):
    """
    some item that has payloads
    """
    payloads: Dict[str, Dict]


class Payload(BaseModel, ABC):
    """
    strong typed payload protocol
    """
    key: ClassVar[str]
    """ the unique key of the payload"""

    @classmethod
    def read_payload(cls, message: Union[Message, HasPayloads]) -> Optional[Self]:
        value = message.payloads.get(cls.key, None)
        if value is None:
            return None
        return cls(**value)

    def set_payload(self, message: Union[Message, HasPayloads]) -> None:
        message.payloads[self.key] = self.model_dump()

    @classmethod
    def payload_exists(cls, message: Union[Message, HasPayloads]) -> bool:
        if not hasattr(message, "payloads"):
            return False
        if not isinstance(message.payloads, dict):
            return False
        return cls.key in message.payloads
