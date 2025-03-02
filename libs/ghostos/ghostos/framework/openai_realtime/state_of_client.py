from __future__ import annotations
from typing import List, Optional, Protocol
from typing_extensions import Self
from abc import ABC, abstractmethod
from ghostos.framework.openai_realtime.configs import OpenAIRealtimeAppConf
from ghostos.core.runtime import Event as GhostOSEvent
from ghostos.abcd.realtime import Operator, OperatorName
from ghostos.contracts.logger import LoggerItf
from enum import Enum


class AppState(str, Enum):
    created = "created"
    closed = "closed"

    connecting = "connecting"
    """connecting to the websocket server"""

    synchronizing = "synchronizing"
    """synchronizing conversation with the websocket server"""

    waiting_response = "waiting response"

    updating = "updating"
    """updating the local conversation from server state"""

    listening = "listening"
    """listening on the local audio inputs"""

    responding = "responding"
    """responding from the server"""

    idle = "idle"

    function_call = "function calling"
    """local conversation function call"""


listen_op = OperatorName.listen.new("start listening and sending audio buffer")
respond_op = OperatorName.respond.new("create a response")
clear_audio_op = OperatorName.clear_audio.new("clear input audio buffer")
stop_listen_op = OperatorName.stop_listen.new("stop listening but do nothing.")
cancel_response_op = OperatorName.cancel_responding.new("cancel current responding")


class Client(Protocol):
    conf: OpenAIRealtimeAppConf
    logger: LoggerItf

    @abstractmethod
    def reconnect(self) -> None:
        """
        recreate the ws connection.
        :return:
        """
        pass

    @abstractmethod
    def vad_mode(self) -> bool:
        pass

    @abstractmethod
    def update_session(self):
        pass

    @abstractmethod
    def synchronize_server_session(self):
        """
        :return:
        """
        pass

    @abstractmethod
    def cancel_responding(self) -> bool:
        """
        cancel server responding and local output
        :return:
        """
        pass

    @abstractmethod
    def start_listening(self) -> bool:
        pass

    @abstractmethod
    def stop_listening(self) -> bool:
        pass

    @abstractmethod
    def is_listening(self) -> bool:
        pass

    @abstractmethod
    def listen_mode(self) -> bool:
        pass

    @abstractmethod
    def is_server_responding(self) -> bool:
        pass

    def is_responding(self) -> bool:
        return self.is_server_responding() or self.is_speaking()

    @abstractmethod
    def is_speaking(self) -> bool:
        pass

    @abstractmethod
    def audio_buffer_append(self, buffer: bytes) -> None:
        pass

    @abstractmethod
    def commit_audio_input(self) -> bool:
        """
        and stop listening.
        :return:
        """
        pass

    @abstractmethod
    def clear_audio_input(self) -> bool:
        pass

    @abstractmethod
    def create_response(self) -> bool:
        pass

    @abstractmethod
    def receive_server_event(self) -> bool:
        pass

    @abstractmethod
    def respond_error_message(self, error: str) -> None:
        pass

    @abstractmethod
    def handle_ghostos_event(self, event: GhostOSEvent):
        pass


class StateOfClient(ABC):

    def __init__(
            self,
            client: Client,
    ):
        self.client = client

    @abstractmethod
    def on_init(self):
        """
        同步阻塞逻辑.
        """
        pass

    @abstractmethod
    def state_name(self) -> str:
        """

        :return:
        """
        pass

    def recv_server_event(self) -> bool:
        return self.client.receive_server_event()

    @abstractmethod
    def operate(self, operator: Operator) -> Optional[Self]:
        pass

    def allow(self, operator: Operator) -> bool:
        operators = self.operators()
        return operator.name in {op.name for op in operators}

    @abstractmethod
    def operators(self) -> List[Operator]:
        pass

    @abstractmethod
    def tick_frame(self) -> Optional[Self]:
        pass

    def destroy(self):
        self.client = None

    def default_mode(self) -> Self:
        if self.client.listen_mode():
            # start vad mode and listening to anything.
            return ListeningState(self.client)
        else:
            # wait for user's operator.
            return IdleState(self.client)


class ConnectingState(StateOfClient):
    """
    connecting the websocket server
    """

    def state_name(self) -> str:
        # when connecting nothing is able to do.
        return AppState.connecting.value

    def on_init(self):
        self.client.reconnect()

    def allow(self, operator: str) -> bool:
        return False

    def operate(self, operator: str) -> Optional[Self]:
        return None

    def recv_server_event(self) -> bool:
        return False

    def operators(self) -> List[str]:
        return []

    def tick_frame(self) -> Optional[Self]:
        return SynchronizingState(self.client)


class SynchronizingState(StateOfClient):
    """
    synchronizing conversation history to the websocket server
    """

    def state_name(self) -> str:
        return AppState.synchronizing.value

    def allow(self, operator: str) -> bool:
        return False

    def recv_server_event(self) -> bool:
        return False

    def operate(self, operator: str) -> Optional[Self]:
        return None

    def operators(self) -> List[str]:
        return []

    def on_init(self):
        self.client.synchronize_server_session()

    def tick_frame(self) -> Optional[Self]:
        return self.default_mode()


class ListeningState(StateOfClient):

    def on_init(self):
        self.client.start_listening()

    def state_name(self) -> str:
        return AppState.listening.value

    def operators(self) -> List[str]:
        return [
            respond_op,
            stop_listen_op,
            clear_audio_op,
        ]

    def operate(self, operator: Operator) -> Optional[Self]:
        name = operator.name
        if name == OperatorName.respond.value:
            # commit and create response.
            return CreateResponseState(self.client)

        elif name == OperatorName.stop_listen:
            # stop listening, and do nothing.
            # do not clear the input audio buffer automatically.
            self.client.stop_listening()
            return IdleState(self.client)

        elif name == OperatorName.clear_audio:
            self.client.clear_audio_input()
            # clear and stay idle
            return IdleState(self.client)

        else:
            return None

    def tick_frame(self) -> Optional[Self]:
        if self.client.is_server_responding():
            # responding not cancel listening
            return RespondingState(self.client)
        if not self.client.listen_mode():
            return self.default_mode()
        return None


class CreateResponseState(StateOfClient):

    def on_init(self):
        if self.client.is_server_responding():
            # if create response while responding, cancel current one first.
            self.client.cancel_responding()
        elif self.client.is_listening():
            # if create response while listening, commit it
            self.client.commit_audio_input()

        # create response.
        self.client.create_response()
        return

    def state_name(self) -> str:
        return str(AppState.waiting_response.value)

    def operate(self, operator: Operator) -> Optional[Self]:
        return None

    def operators(self) -> List[Operator]:
        # when creating responding, no operators allowed.
        return []

    def tick_frame(self) -> Optional[Self]:
        if self.client.is_server_responding():
            return RespondingState(self.client)
        return None


class RespondingState(StateOfClient):

    def on_init(self):
        if not self.client.is_server_responding():
            self.client.respond_error_message("enter responding state but server is not responding")
        return

    def state_name(self) -> str:
        return str(AppState.responding.value)

    def operate(self, operator: Operator) -> Optional[Self]:
        name = operator.name
        if name == OperatorName.cancel_responding.value:
            # cancel current responding.
            if self.client.is_responding():
                self.client.cancel_responding()
            return self.default_mode()

        elif name == OperatorName.listen.value:
            if self.client.is_responding():
                self.client.cancel_responding()
            return ListeningState(self.client)
        else:
            return None

    def operators(self) -> List[Operator]:
        return [
            cancel_response_op,
            listen_op,
        ]

    def tick_frame(self) -> Optional[Self]:
        if self.client.is_responding():
            return None
        else:
            self.client.logger.debug("responding state return default mode")
            return self.default_mode()


class IdleState(StateOfClient):

    def on_init(self):
        if self.client.is_listening():
            self.client.stop_listening()
        elif self.client.is_responding():
            self.client.cancel_responding()

    def state_name(self) -> str:
        return AppState.idle.value

    def operate(self, operator: Operator) -> Optional[Self]:
        if operator.name == OperatorName.listen.value:
            return ListeningState(self.client)
        elif operator.name == OperatorName.respond.value:
            return CreateResponseState(self.client)
        return None

    def operators(self) -> List[Operator]:
        return [
            listen_op,
            respond_op,
        ]

    def tick_frame(self) -> Optional[Self]:
        if self.client.is_listening():
            return ListeningState(self.client)
        return None
