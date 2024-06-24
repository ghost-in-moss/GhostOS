from abc import ABC
from typing import ClassVar, Optional
from pydantic import BaseModel
from ghostiss.blueprint.messages.message import Message

__all__ = ["Attachment"]


class Attachment(BaseModel, ABC):
    """
    message attachment
    """

    attach_key: ClassVar[str] = ""

    @classmethod
    def retrieve(cls, msg: Message) -> Optional["Attachment"]:
        """
        retrieve attachment from message
        """
        if cls.attach_key in msg.attachments:
            return cls(**msg.attachments[cls.attach_key])
        return None

    def set(self, msg: Message) -> None:
        """
        set attachment to message
        """
        msg.attachments[self.attach_key] = self.model_dump()
