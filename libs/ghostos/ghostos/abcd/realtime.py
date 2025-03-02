from __future__ import annotations
from abc import ABC, abstractmethod
from typing import (
    Generic,
    List, Iterable, Tuple, TypeVar, Optional, Dict, Callable, Union
)
from typing_extensions import Self
from ghostos.abcd import Conversation
from ghostos.core.messages import Message, ReceiverBuffer
from ghostos_common.entity import ModelEntityMeta, to_entity_model_meta, from_entity_model_meta
from pydantic import BaseModel, Field
from enum import Enum


class Realtime(ABC):
    """
    realtime wrapper
    """

    @abstractmethod
    def create(
            self,
            conversation: Conversation,
            listener: Listener,
            speaker: Speaker,
            app_name: str = "",
            config: Optional[RealtimeAppConfig] = None,
    ) -> RealtimeApp:
        """
        create an Realtime App instance
        :param conversation:
        :param listener:
        :param speaker:
        :param app_name:
        :param config:
        :return:
        """
        pass

    @abstractmethod
    def get_config(self) -> RealtimeConfig:
        pass

    @abstractmethod
    def register(self, driver: RealtimeDriver):
        pass


class RealtimeAppConfig(BaseModel):

    @abstractmethod
    def driver_name(self) -> str:
        pass


class RealtimeConfig(BaseModel):
    default: str = Field(description="default app")
    apps: Dict[str, ModelEntityMeta] = Field(
        default_factory=dict,
    )

    def add_app_conf(self, name: str, app_conf: RealtimeAppConfig):
        self.apps[name] = to_entity_model_meta(app_conf)

    def get_app_conf(self, name: str) -> Optional[RealtimeAppConfig]:
        data = self.apps.get(name, None)
        if data is None:
            return None
        conf = from_entity_model_meta(data)
        if not isinstance(conf, RealtimeAppConfig):
            raise TypeError(f"App config {name} is not a RealtimeAppConfig")
        return conf


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
            vad_mode: bool = False,
    ) -> RealtimeApp:
        pass


class Listener(ABC):
    """
    read audio bytes
    """

    @abstractmethod
    def listen(self, sender: Callable[[bytes], None]) -> Listening:
        """
        read audio bytes in seconds.
        :param sender: sender hearing data
        :return:
        """
        pass


class Listening(ABC):
    @abstractmethod
    def __enter__(self) -> Self:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class Speaker(ABC):

    @abstractmethod
    def speak(self, queue: Callable[[], Union[bytes, None]]) -> Speaking:
        pass


class Speaking(ABC):
    @abstractmethod
    def __enter__(self) -> Self:
        """
        start to speak
        :return:
        """
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def done(self) -> bool:
        pass

    @abstractmethod
    def wait(self):
        pass


class Operator(BaseModel):
    name: str = Field(description="name of the operator")
    description: str = Field(description="description of the operator")


class OperatorName(str, Enum):
    listen = "listen"
    """start listening"""

    stop_listen = "stop listen"
    """stop listening, commit the audio buffer, but not create response"""

    respond = "respond"
    """create response"""

    clear_audio = "clear"
    """clear audio buffer """

    cancel_responding = "cancel"
    """cancel responding"""

    def new(self, description: str) -> Operator:
        return Operator(name=self.value, description=description)


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

    conversation: Conversation

    @property
    @abstractmethod
    def vad_mode(self) -> bool:
        pass

    @property
    @abstractmethod
    def listen_mode(self) -> bool:
        pass

    @abstractmethod
    def start(self, vad_mode: bool = True, listen_mode: bool = True) -> Operator:
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
    def history_messages(self) -> Iterable[Message]:
        """
        return history messages.
        """
        pass

    @abstractmethod
    def set_mode(self, *, vad_mode: Optional[bool] = None, listen_mode: Optional[bool] = None):
        pass

    @abstractmethod
    def state(self) -> Tuple[str, List[Operator]]:
        """
        :return: (operators, operators)
        """
        pass

    @abstractmethod
    def operate(self, operator: Operator) -> bool:
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
    def add_message(self, message: Message, previous_message_id: Optional[str] = None):
        """
        add message to the conversation.
        :param message:
        :param previous_message_id:
        :return:
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
