from __future__ import annotations
from abc import ABC, abstractmethod
from typing import (
    Generic,
    Protocol, Literal, List, ClassVar, Iterable, Tuple, TypeVar, Optional, Dict, Callable, Type,
    Self,
    Union,
)
from ghostos.abcd import Conversation
from ghostos.core.messages import Message, ReceiverBuffer
import time
from enum import Enum
from pydantic import BaseModel, Field
from queue import Queue
from contextlib import contextmanager


# class State(ABC):
#     state_name: ClassVar[str]
#
#     @abstractmethod
#     def conversation(self) -> Conversation:
#         pass
#
#     @abstractmethod
#     def operate(self, op: Operator) -> Tuple[str, str | None]:
#         """
#         :param op:
#         :return: accept level | error message
#         """
#         pass
#
#     @abstractmethod
#     def run_operator(self) -> Union["State", None]:
#         """
#         :return: None means no operation, go on handle event
#         """
#         pass
#
#     @abstractmethod
#     def run_server_event(self) -> Union[State, None]:
#         """
#         :return: a new state, or continue
#         """
#         pass
#
#     def tick(self) -> Union[State, None]:
#         """
#         :return: if not none, means a new state is returned. and:
#         1. replace current state with new state
#         2. put the current state to a recycling queue, join it without blocking.
#         """
#         new_state = self.run_operator()
#         if new_state:
#             return new_state
#         new_state = self.run_server_event()
#         if new_state:
#             return new_state
#         return None
#
#     @abstractmethod
#     def join(self):
#         """
#         """
#         pass
#
#
# S = TypeVar("S", bound=State)


class Realtime(ABC):
    @abstractmethod
    def create(self, conversation: Conversation, app_name: str = "") -> RealtimeApp:
        pass

    @abstractmethod
    def register(self, driver: RealtimeDriver):
        pass


class RealtimeAppConfig(BaseModel):

    @abstractmethod
    def driver_name(self) -> str:
        pass


class RealtimeConfig(BaseModel):
    apps: Dict[str, RealtimeAppConfig] = Field(
        default_factory=dict,
    )


C = TypeVar("C", bound=RealtimeAppConfig)


class RealtimeDriver(Generic[C], ABC):

    @abstractmethod
    def driver_name(self) -> str:
        pass

    @abstractmethod
    def create(
            self,
            config: C,
            conversation: Conversation,
            listener: Optional[Listener] = None,
            speaker: Optional[Speaker] = None,
    ) -> RealtimeApp:
        pass


class Listener(ABC):

    @abstractmethod
    def hearing(self) -> Optional[bytes]:
        pass

    @abstractmethod
    def flush(self) -> bytes:
        pass

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class Speaker(ABC):
    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    def speak(self, data: bytes):
        pass

    @abstractmethod
    def flush(self) -> bytes:
        pass


class RealtimeOP(Protocol):
    name: str
    description: str


class RealtimeApp(ABC):
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
    def start(self):
        """
        start realtime session
        """
        pass

    @abstractmethod
    def close(self):
        """
        close realtime session and release resources
        """
        pass

    @abstractmethod
    def is_closed(self) -> bool:
        pass

    @abstractmethod
    def messages(self) -> Iterable[Message]:
        """
        return history messages.
        """
        pass

    @abstractmethod
    def state(self) -> Tuple[str, List[str]]:
        """
        :return: (operators, operators)
        """
        pass

    @abstractmethod
    def operate(self, operator: str) -> bool:
        """
        run operator.
        """
        pass

    @abstractmethod
    def fail(self, error: Exception) -> bool:
        """
        receive an exception
        :return: if the error is able to intercept
        """
        pass

    @abstractmethod
    def output(self) -> Optional[ReceiverBuffer]:
        """
        output messages. if None, check status again.
        """
        pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        intercepted = None
        if exc_val is not None:
            intercepted = self.fail(exc_val)
        self.close()
        return intercepted


def example(app: RealtimeApp):
    with app:
        while True:
            state, ops = app.state()
            print(state, ops)
            outputting = app.output()
            if outputting is None:
                time.sleep(0.1)
                continue
            while outputting is not None:
                print(outputting.head())
                chunks = outputting.chunks()
                for c in chunks:
                    print(c)
                print(outputting.tail())


def streamlit_example(app: RealtimeApp):
    import streamlit as st
    with app:
        for message in app.messages():
            with st.container():
                st.write(message)

        while True:
            with st.empty():
                rendered = False
                while not rendered:
                    state, operators = app.state()
                    with st.container():
                        if operators:
                            for op in operators:
                                st.write(op)
                        with st.status(state):
                            buffer = app.output()
                            if buffer is None:
                                continue
                            rendered = buffer
                            if rendered is None:
                                time.sleep(0.1)
                            else:
                                break
                with st.container():
                    st.write(buffer.tail())
                break
