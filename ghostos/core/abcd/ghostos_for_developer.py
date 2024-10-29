from __future__ import annotations
from typing import Protocol, Callable, Optional, Literal, Union, Iterable, Type, TypeVar, ClassVar, Generic
from abc import ABC, abstractmethod
from pydantic import BaseModel
from ghostos.container import Container
from ghostos.common import Identifiable, Identifier
from .kernel import Ghost
from .ghostos_for_ai import Task

MessageTypes = Union[str,]

G = TypeVar("G", bound=Ghost)


class GhostOS(Protocol):
    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    def get_agent(self, name: str = "") -> Agent:
        pass

    @abstractmethod
    def set_agent(self, name: str, agent: Agent) -> None:
        pass

    @abstractmethod
    def get_ghost(self, route: str) -> GhostFunc:
        pass

    @abstractmethod
    def converse(
            self,
            agent: Union[Agent, str, None] = None,
            ghost: Union[GhostFunc, str, None] = None,
            args: Union[dict, BaseModel] = None,
            session_id: Optional[str] = None,
            parent_id: Optional[str] = None,
    ) -> Conversation:
        pass

    @abstractmethod
    def call(
            self,
            ghost: G,
            args: Union[dict, G.Args],
            run_until_complete: bool = True,
            state: Optional[State[G]] = None
    ) -> State[G]:
        pass


class Event(Protocol):
    event_id: str
    type: str


class Agent(Identifiable, ABC):

    def meta_instruction(self) -> str:
        pass

    def ghost_id(self) -> Union[str, None]:
        pass


class Turn(BaseModel):
    id: str
    event: Optional[Event]
    messages: list[Message]


class Thread(Protocol):
    turns: list[Turn]


class State(Generic[G]):
    id: str
    status: Literal['']
    args: G.Args
    ghost: G
    returns: G.Returns


class Conversation(Protocol[Ghost]):
    @abstractmethod
    def state(self) -> State:
        pass

    @abstractmethod
    def thread(self) -> Thread:
        pass

    @abstractmethod
    def update(self, args: Union[Ghost.Args, dict]) -> State:
        pass

    @abstractmethod
    def chat(self, *messages: MessageTypes, chunks: bool = True) -> Iterable[Message]:
        pass

    @abstractmethod
    def handle_event(self, event: Event, chunks: bool = True) -> Iterable[Message]:
        pass

    @abstractmethod
    def recv_event(self, event: Event, peek: bool = True) -> Optional[Event]:
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def closed(self) -> bool:
        pass

    @abstractmethod
    def fail(self, error: Exception) -> bool:
        pass

    @abstractmethod
    def save(self):
        pass
