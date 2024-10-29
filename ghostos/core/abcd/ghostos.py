from __future__ import annotations
from typing import Protocol, Optional, Iterable, List
from abc import ABC, abstractmethod
from ghostos.container import Container
from ghostos.entity import EntityMeta


class GhostOS(ABC):

    @abstractmethod
    def converse(
            self,
            conversable: Conversable,
            process_id: Optional[str] = None,
    ) -> Conversation:
        pass


class Conversable(Protocol):

    @abstractmethod
    def on_event(self, runtime: Runtime, event: Event) -> Optional[Operator]:
        pass


class Event(Protocol):
    pass


class Message(Protocol):
    pass


class Runtime(Protocol):

    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    def frame(self) -> Frame:
        pass

    @abstractmethod
    def save_frame(self, frame: Frame) -> None:
        pass


class Frame(Protocol):
    frame_id: str
    args: dict
    state: dict
    result: Optional[dict]
    status: str
    children: List[str]
    conversable: EntityMeta


class Operator(Protocol):

    @abstractmethod
    def run(self, runtime: Runtime) -> Optional[Operator]:
        pass


class Conversation(Protocol):
    id: str
    args: dict
    state: dict
    result: Optional[dict]
    status: str

    @abstractmethod
    def messages(self) -> Iterable[Message]:
        pass

    @abstractmethod
    def handle_event(self, event: Event) -> Iterable[Message]:
        pass

    @abstractmethod
    def send_event(self, event: Event) -> None:
        pass

    @abstractmethod
    def pop_event(self, event: Event) -> Optional[Event]:
        pass
