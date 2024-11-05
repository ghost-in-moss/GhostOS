from typing import Optional, Iterable, List, Callable, Self
from abc import ABC, abstractmethod
from ghostos.common import Identical, Identifier
from ghostos.core.session import (
    Event,
)
from ghostos.core.messages import Message
from ghostos.container import Container, Contracts


class Agent(Identical, ABC):

    @abstractmethod
    def identifier(self) -> Identifier:
        pass

    @abstractmethod
    def instruction(self) -> str:
        pass

    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    def run(self, history: List[Message], inputs: Iterable[Message]) -> Iterable[Message]:
        pass


class StatefulAgent(Agent, ABC):

    @abstractmethod
    def on_inputs(self, inputs: Iterable[Message]) -> Iterable[Message]:
        pass

    @abstractmethod
    def pop_event(self) -> Optional[Event]:
        pass

    @abstractmethod
    def handle_event(self, event: Event) -> None:
        pass


class Realtime(ABC):

    @abstractmethod
    def on_event(self, callback: Callable[[StatefulAgent, Event], Optional[Event]]) -> None:
        pass

    @abstractmethod
    def on_message(self, callback: Callable[[StatefulAgent, Message], None]) -> None:
        pass

    @abstractmethod
    def on_message_chunks(
            self,
            msg_type: str,
            callback: Callable[[StatefulAgent, Iterable[Message]], None],
    ) -> None:
        pass

