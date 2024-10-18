from abc import abstractmethod
from typing import Iterable, Callable, List, Optional
from typing_extensions import Literal, Protocol, Self

__all__ = [
    "Message",
]


class Message(Protocol):
    """
    消息协议中的最小传输单元.
    """

    @abstractmethod
    def get_seq(self) -> Literal["head", "chunk", "complete"]:
        pass

    @abstractmethod
    def get_copy(self) -> Self:
        pass


class Parser(Protocol):

    @abstractmethod
    def batch(self, messages: Iterable[Message]) -> Iterable[Message]:
        pass

    @abstractmethod
    def parse(self, message: Message) -> Iterable[Message]:
        pass

    @abstractmethod
    def completes(self) -> List[Message]:
        pass


class Connection(Protocol):

    @abstractmethod
    def on_message(self, callback: Callable[[Message], None]):
        pass

    @abstractmethod
    def on_error(self, callback: Callable[[Message], None]):
        pass

    @abstractmethod
    def send(self, inputs: Iterable[Message]) -> None:
        pass

    @abstractmethod
    def cancel(self, error: Optional[str]) -> None:
        pass

    @abstractmethod
    def wait(
            self,
            on_message: Optional[Callable[[Message], None]] = None,
            on_error: Optional[Callable[[Message], None]] = None,
    ) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def closed(self) -> bool:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.closed():
            return
        if exc_val is not None:
            self.cancel(error=str(exc_val))
        self.close()


class Request(Protocol):

    @abstractmethod
    def ack(self) -> None:
        pass

    @abstractmethod
    def inputs(self) -> Iterable[Message]:
        pass

    @abstractmethod
    def write(self, messages: Iterable[Message]) -> None:
        pass

    @abstractmethod
    def done(self) -> None:
        pass

    @abstractmethod
    def fail(self, error: str) -> None:
        pass

    @abstractmethod
    def buffer(self) -> List[Message]:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def closed(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.closed():
            return
        if exc_val is not None:
            self.fail(error=str(exc_val))
        self.close()


class Server(Protocol):

    def run(self, func: Callable[[Request], None]) -> Connection:
        pass
