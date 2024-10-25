from __future__ import annotations
from abc import ABC, abstractmethod
from typing import (
    Protocol, Literal, List, ClassVar, Iterable, Tuple, TypeVar, Optional, Dict, Callable, Type,
    Union,
)
from enum import Enum
from pydantic import BaseModel
from queue import Queue


class Message(Protocol):
    msg_id: str
    type: str
    role: str
    seq: Literal["head", "chunk", "complete"]


class SessionProtocol(Protocol):
    instructions: str
    shell_funcs: Dict[str, List[Function]]


S = TypeVar("S", bound=SessionProtocol)
M = TypeVar("M", bound=Message)


class RealtimeAgent(Protocol[S, M]):
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
            session: S,
            conversation: Optional[ConversationProtocol] = None,
            *shells: Shell,
    ) -> None:
        pass


class ConversationProtocol(Protocol[M]):

    @abstractmethod
    def id(self) -> str:
        pass

    @abstractmethod
    def messages(self) -> Iterable[M]:
        pass

    @abstractmethod
    def append(self, message: M) -> None:
        pass

    @abstractmethod
    def save(self):
        """
        save to local storage or do nothing.
        """
        pass


class Function(Protocol):
    name: str
    description: str
    parameters: Dict


class Status(str, Enum):
    """
    state of the agent.
    realtime agent is basically a state machine.
    each state has it's policy for operations.
    like:
    - stopped: means no operation allowed anymore
    - connecting: is not ready yet, can not send event or receive message
    - available: is ready for most operations.
    """
    AVAILABLE = "available"
    CONNECTING = "connecting"
    STOPPED = "stopped"


T = TypeVar("T", bound=Status)


class Ghost(Protocol[S, M, T]):

    @abstractmethod
    def alive(self) -> bool:
        pass

    @abstractmethod
    def status(self) -> T:
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
    def messages(self) -> Iterable[M]:
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
    def on_sync(self, ghost: Ghost) -> Queue:
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


class Operator(ABC):
    """
    to operate the agent's ghost state machine
    is a protocol defined by the agent.

    """
    pass


class Stop(Operator):
    pass


class Reconnect(Operator):
    pass


class FunctionOutput(BaseModel, Operator):
    id: Optional[str]
    name: str
    content: str
