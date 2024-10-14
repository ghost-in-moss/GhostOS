from abc import abstractmethod
from typing import Iterable, Optional
from typing_extensions import Protocol
from .transport import Message
from ghostos.abc import Identifier

__all__ = ("Actor", "Address", "Topic", "Mail")


class Address(Protocol):
    """
    instance of the actor
    """

    @abstractmethod
    def identifier(self) -> Identifier:
        pass


class Topic(Protocol):
    """
    topic that transport messages
    """

    @abstractmethod
    def identifier(self) -> Identifier:
        pass

    @abstractmethod
    def get_parent(self) -> Optional[str]:
        pass


class Mail(Protocol):

    @abstractmethod
    def issuer(self) -> Optional[Address]:
        pass

    @abstractmethod
    def receiver(self) -> Optional[Address]:
        pass

    @abstractmethod
    def topic(self) -> Topic:
        pass

    @abstractmethod
    def content(self) -> Iterable[Message]:
        pass


class ActCtx(Protocol):

    @abstractmethod
    def topics(self) -> Iterable[Topic]:
        pass


class Actor(Protocol):

    @abstractmethod
    def identifier(self) -> Identifier:
        pass

    @abstractmethod
    def on_recv(
            self,
            ctx: ActCtx,
            recv: Mail,
    ) -> Iterable[Message]:
        """
        回复一个邮件
        """
        pass
