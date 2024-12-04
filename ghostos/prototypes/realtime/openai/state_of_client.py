from __future__ import annotations
from typing import List, Optional, Tuple, Protocol, Self
from abc import ABC, abstractmethod
from .configs import OpenAIRealtimeConf
from ghostos.core.messages import Message
from enum import Enum


class AppState(str, Enum):
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
    conf: OpenAIRealtimeConf

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
    def update_local_conversation(self) -> None:
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
    def is_responding(self) -> bool:
        pass

    @abstractmethod
    def receive_server_event(self) -> bool:
        pass

    @abstractmethod
    def send_error_message(self, error: str) -> None:
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
    def status(self) -> str:
        """

        :return:
        """
        pass

    def rotate(self) -> bool:
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
        elif self.client.is_responding():
            return RespondingState(self.client)
        else:
            return IdleState(self.client)


class ConnectingState(StateOfClient):
    """
    connecting the websocket server
    """

    def status(self) -> str:
        # when connecting nothing is able to do.
        return AppState.connecting.value

    def on_init(self):
        self.client.reconnect()

    def allow(self, operator: str) -> bool:
        return False

    def operate(self, operator: str) -> Optional[Self]:
        return None

    def rotate(self) -> bool:
        return False

    def operators(self) -> List[str]:
        return []

    def tick_frame(self) -> Optional[Self]:
        return SynchronizingState(self.client)


class SynchronizingState(StateOfClient):
    """
    synchronizing conversation history to the websocket server
    """

    def status(self) -> str:
        return AppState.synchronizing.value

    def allow(self, operator: str) -> bool:
        return False

    def rotate(self) -> bool:
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

    def status(self) -> str:
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
        if self.client.is_responding():
            # responding not cancel listening
            return RespondingState(self.client)
        return None


class CreateResponseState(StateOfClient):

    def on_init(self):
        if self.client.is_responding():
            self.client.cancel_responding()
        if self.client.is_listening():
            self.client.commit_audio_input()
        self.client.create_response()
        return

    def status(self) -> Tuple[str, List[str]]:
        return AppState.waiting_response, self.operators()

    def operate(self, operator: str) -> Optional[Self]:
        # todo: test later
        return None

    def operators(self) -> List[str]:
        # todo: test later
        return []

    def tick_frame(self) -> Optional[Self]:
        if self.client.is_responding():
            return RespondingState(self.client)
        return None


class RespondingState(StateOfClient):

    def on_init(self):
        if not self.client.is_responding():
            self.client.send_error_message("enter responding state but server is not responding")
        return

    def status(self) -> str:
        return AppState.responding.value

    def operate(self, operator: str) -> Optional[Self]:
        if operator == OperatorName.cancel_responding.value:
            if self.client.is_responding():
                self.client.cancel_responding()
            return self.default_mode()
        elif operator == OperatorName.listen.value:
            if self.client.is_responding():
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
        if self.client.is_responding():
            return None
        else:
            return self.default_mode()


class IdleState(StateOfClient):

    def on_init(self):
        if self.client.is_listening():
            self.client.stop_listening()
        elif self.client.is_responding():
            self.client.cancel_responding()
        # when idle, update local conversation.
        self.client.update_local_conversation()
        return

    def status(self) -> str:
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
        self.client.update_local_conversation()
        return None
