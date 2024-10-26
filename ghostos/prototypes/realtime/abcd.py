from __future__ import annotations
from abc import ABC, abstractmethod
from typing import (
    Protocol, Literal, List, ClassVar, Iterable, Tuple, TypeVar, Optional, Dict, Callable, Type,
    Self,
    Union,
)
import time
from enum import Enum
from pydantic import BaseModel
from queue import Queue
from contextlib import contextmanager


class Message(Protocol):
    msg_id: str
    type: str
    role: str
    seq: Literal["head", "chunk", "complete"]


class State(ABC):
    state_name: ClassVar[str]

    @abstractmethod
    def conversation(self) -> ConversationProtocol:
        pass

    @abstractmethod
    def status(self) -> str:
        """
        if there are sub statuses of this State
        :return:
        """
        pass

    @abstractmethod
    def operate(self, op: Operator) -> Tuple[Literal["", "queued", "blocked", "illegal"], str | None]:
        """
        :param op:
        :return: accept level | error message
        """
        pass

    @abstractmethod
    def run_operator(self) -> Union["State", None]:
        """
        :return: None means no operation, go on handle event
        """
        pass

    @abstractmethod
    def run_server_event(self) -> Union[State, None]:
        """
        :return: a new state, or continue
        """
        pass

    def tick(self) -> Union[State, None]:
        """
        :return: if not none, means a new state is returned. and:
        1. replace current state with new state
        2. put the current state to a recycling queue, join it without blocking.
        """
        new_state = self.run_operator()
        if new_state:
            return new_state
        new_state = self.run_server_event()
        if new_state:
            return new_state
        return None

    @abstractmethod
    def join(self):
        """
        clear/recycle/release resources when a state is overdue
        """
        pass


S = TypeVar("S", bound=State)


class RealtimeAgent(Protocol[S]):
    """
    realtime agent in multi-threading programming pattern.
    it will develop several threads during runtime to exchange parallel events and actions.

    furthermore this agent programming model allow parallel `body parts` (shells). for examples:
    - an OS-based listen-speak channel
    - a website that shows the conversation items, and allow to input text message.
    - an async channel to call function like multi-agent based-on different models
    - a real material body that controlled by a running robot OS

    all the cases are running concurrently in a single agent.
    otherwise the realtime api is no more than a block mode chat agent, why the complexities?

    although the shells are parallel running, event sending and receiving are concurrent,
    but the agent itself is still stateful, or facing brain split failures.

    the operations to the agent may be:
    1. act immediately
    2. illegal for current state
    3. allowed but pending
    4. allowed but blocking, need retry later
    5. etc...

    the safest way to develop the agent FSM is frame-based model. broadly used in the realtime games.
    the agent tick a frame to do an operation or recv an event, if None then idle a while before next tick.
    operations are prior to events.

    in the other hand the shell (bodies) has its own state machine in the same way,
    but could use success-or-failure pattern, much simpler.

    although the OpenAI realtime session itself is stateful, but it does not keep a long-time session,
    so the client side agent implementation need to do all the state work itself,
    make sure the session is aligned to server session in the duplex way.
    that why we need a full-functional state machine in our agent's implementation.
    so the client side agent is the real central state machine in the long-term,
    but yield its privilege to server side session during runtime.
    """

    @abstractmethod
    def run_util_stop(
            self,
            conversation: Optional[ConversationProtocol] = None,
            *shells: Shell,
    ) -> None:
        pass


class ConversationProtocol(Protocol):

    @abstractmethod
    def id(self) -> str:
        pass

    @abstractmethod
    def messages(self) -> Iterable[Message]:
        pass

    @abstractmethod
    def append(self, message: Message) -> None:
        pass

    @abstractmethod
    def save(self):
        """
        save to local storage or do nothing.
        """
        pass


class Function(BaseModel):
    name: str
    description: str
    parameters: Dict

    def with_name(self, name: str) -> Self:
        return self.model_copy(update={"name": name}, deep=True)


class Ghost(Protocol):

    @abstractmethod
    def alive(self) -> bool:
        pass

    @abstractmethod
    def status(self) -> str:
        pass

    @abstractmethod
    def operate(self, op: Operator) -> Tuple[str, bool]:
        pass

    @abstractmethod
    def allow(self, op: Type[Operator]) -> bool:
        pass

    @abstractmethod
    def session(self) -> S:
        pass

    @abstractmethod
    def messages(self) -> Iterable[Message]:
        pass


class Shell(Protocol):
    id: str
    name: str
    description: str

    @abstractmethod
    def functions(self) -> Iterable[Function]:
        pass

    @abstractmethod
    def subscribing(self) -> List[str]:
        pass

    @abstractmethod
    def on_sync(self, ghost: Ghost) -> ChanOut[Union[dict, None]]:
        """
        sync the ghost with shell,
        and return a channel that the agent publish the subscribed event to the shell.
        :param ghost:
        :return: Queue[event: dict, None]. None means the agent is stopped.
        """
        pass


class FunctionCall(Protocol):
    id: Optional[str]
    name: str
    arguments: str


# --- channels --- #

E = TypeVar("E")


class ChanIn(Protocol[E]):
    """
    the receiver create the put chan
    compatible to queue.Queue
    but not necessary?
    """

    @abstractmethod
    def put(self, item: E, block=True, timeout=None) -> None:
        """
        :param item: dict | None
        :param block: boolean
        :param timeout: float | None
        """
        pass

    @abstractmethod
    def task_done(self) -> None:
        """
        notify task is done.
        """
        pass


class ChanOut(Protocol[E]):

    @abstractmethod
    def get(self, block=True, timeout=None) -> E:
        pass

    @abstractmethod
    def get_nowait(self):
        pass


# --- basic operators --- #

class Operator(BaseModel, ABC):
    """
    to operate the agent's ghost state machine
    is a protocol defined by the agent.
    """
    type: str
    shell_id: str = ""
