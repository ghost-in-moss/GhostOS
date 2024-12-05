from __future__ import annotations
from typing import List, Optional, Tuple, Protocol, Self
from abc import ABC, abstractmethod
from .configs import OpenAIRealtimeAppConf
from ghostos.core.runtime import Event as GhostOSEvent
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


class OperatorName(str, Enum):
    listen = "listen"
    commit = "commit"
    stop_listen = "stop listen"
    clear_audio = "clear"
    respond = "respond"
    cancel_responding = "cancel"


class Client(Protocol):
    conf: OpenAIRealtimeAppConf

    @abstractmethod
    def reconnect(self) -> None:
        """
        recreate the ws connection.
        :return:
        """
        pass

    @abstractmethod
    def synchronize_server_session(self):
        """
        :return:
        """
        pass

    @abstractmethod
    def cancel_responding(self) -> bool:
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
    def is_server_responding(self) -> bool:
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
    def operate(self, operator: str) -> Optional[Self]:
        pass

    def allow(self, operator: str) -> bool:
        operators = self.operators()
        return operator in operators

    @abstractmethod
    def operators(self) -> List[str]:
        pass

    @abstractmethod
    def tick_frame(self) -> Optional[Self]:
        pass

    def destroy(self):
        self.client = None

    def default_mode(self) -> Self:
        if self.client.conf.start_mode == "listening":
            return ListeningState(self.client)
        elif self.client.conf.start_mode == "idle":
            return IdleState(self.client)
        elif self.client.is_server_responding():
            return RespondingState(self.client)
        else:
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
            OperatorName.respond,
            OperatorName.stop_listen,
            OperatorName.commit,
            OperatorName.clear_audio,
        ]

    def operate(self, operator: str) -> Optional[Self]:
        if operator == OperatorName.respond.value:
            self.client.commit_audio_input()
            return CreateResponseState(self.client)

        elif operator == OperatorName.commit.value:
            self.client.commit_audio_input()
            self.client.stop_listening()
            return IdleState(self.client)

        elif operator == OperatorName.stop_listen:
            self.client.stop_listening()
            self.client.clear_audio_input()
            return IdleState(self.client)

        elif operator == OperatorName.clear_audio:
            self.client.clear_audio_input()
            # clear and go on listening
            return None

        else:
            return None

    def tick_frame(self) -> Optional[Self]:
        if self.client.is_server_responding():
            # responding not cancel listening
            return RespondingState(self.client)
        return None


class CreateResponseState(StateOfClient):

    def on_init(self):
        if self.client.is_server_responding():
            self.client.cancel_responding()
        if self.client.is_listening():
            self.client.commit_audio_input()
        self.client.create_response()
        return

    def state_name(self) -> Tuple[str, List[str]]:
        return AppState.waiting_response, self.operators()

    def operate(self, operator: str) -> Optional[Self]:
        # todo: test later
        return None

    def operators(self) -> List[str]:
        # todo: test later
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
        return AppState.responding.value

    def operate(self, operator: str) -> Optional[Self]:
        if operator == OperatorName.cancel_responding.value:
            if self.client.is_server_responding():
                self.client.cancel_responding()
            return self.default_mode()
        elif operator == OperatorName.listen.value:
            if self.client.is_server_responding():
                self.client.cancel_responding()
            return ListeningState(self.client)
        else:
            return None

    def operators(self) -> List[str]:
        return [
            OperatorName.cancel_responding,
            OperatorName.listen,
        ]

    def tick_frame(self) -> Optional[Self]:
        if self.client.is_server_responding():
            return None
        else:
            return self.default_mode()


class IdleState(StateOfClient):

    def on_init(self):
        if self.client.is_listening():
            self.client.stop_listening()
        elif self.client.is_server_responding():
            self.client.cancel_responding()
        # when idle, update local conversation.
        return

    def state_name(self) -> str:
        return AppState.idle.value

    def operate(self, operator: str) -> Optional[Self]:
        if operator == OperatorName.listen.value:
            return ListeningState(self.client)
        return None

    def operators(self) -> List[str]:
        return [
            OperatorName.listen.value,
        ]

    def tick_frame(self) -> Optional[Self]:
        if self.client.is_listening():
            return ListeningState(self.client)
        return None
