from typing import ClassVar, Optional, Protocol, Dict, Union
from typing_extensions import Self
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

    @classmethod
    def read_payload_default(cls, message: Union[Message, HasPayloads]) -> Self:
        """
        only for payload class that has default values
        """
        r = cls.read_payload(message)
        if r is None:
            r = cls()
        return r

    def set_payload(self, message: Union[Message, HasPayloads]) -> None:
        message.payloads[self.key] = self.model_dump()

    def set_payload_if_none(self, message: Union[Message, HasPayloads]) -> None:
        if not self.payload_exists(message):
            self.set_payload(message)

    @classmethod
    def payload_exists(cls, message: Union[Message, HasPayloads]) -> bool:
        if not hasattr(message, "payloads"):
            return False
        if not isinstance(message.payloads, dict):
            return False
        return cls.key in message.payloads
