from abc import ABC, abstractmethod

from ghostiss.core.messages.message import Message


class Listener(ABC):
    """
    处理消息体.
    """

    @abstractmethod
    def on_message(self, message: Message) -> None:
        pass
