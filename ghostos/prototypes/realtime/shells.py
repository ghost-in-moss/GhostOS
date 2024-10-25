from abc import abstractmethod
from typing import Protocol, Iterable, Union, Literal
from .abcd import Shell, Message


class Chat(Shell, Protocol):

    @abstractmethod
    def messages(self) -> Iterable[Message]:
        pass

    @abstractmethod
    def pop_message_head(self, timeout: float = 0.0) -> Union[Message, None]:
        pass

    @abstractmethod
    def read_message_chunks(self, msg_id: str) -> Iterable[Message]:
        pass


class TextInput(Shell, Protocol):

    @abstractmethod
    def send(self, text: str):
        pass


class PushOnTalk(Shell, Protocol):

    @abstractmethod
    def state(self) -> Literal["", "recording", "playing", "stopped"]:
        pass

    @abstractmethod
    def start_record(self):
        pass

    @abstractmethod
    def commit(self):
        pass

    @abstractmethod
    def clear(self):
        pass

    @abstractmethod
    def halt(self):
        pass


class AudioOutput(Shell, Protocol):
    @abstractmethod
    def state(self) -> Literal["", "playing"]:
        pass

    @abstractmethod
    def cancel(self):
        pass
