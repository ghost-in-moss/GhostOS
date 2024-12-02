from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Protocol, Optional, Dict
from .event_from_server import *
from .ws import OpenAIWSConnection
from .configs import SessionObject, OpenAIRealtimeConf
from .context import Context
from ghostos.core.messages import Message
from ghostos.abcd import Conversation, GoThreadInfo
from queue import Queue


class ServerState(Protocol):
    ctx: Context

    @abstractmethod
    def recv(self, event: dict):
        """
        recv an openai realtime server event, and handle it.
        recv one server event at a time globally.
        :param event:
        :return:
        """
        pass

    @abstractmethod
    def gc(self):
        pass

    def recv_invalid_event(self, event: dict):
        pass

    def ack_server_event(self, event: ServerEvent):
        pass


class SessionState(ServerState, Protocol):
    """
    session is the root of server state
    """
    session_obj: SessionObject
    conversation: ConversationState
    rate_limit: Optional[dict]
    input_audio: InputAudioBuffer
    status: Literal["new", "updated", "closed"]

    def recv(self, event: dict):
        type_name = ServerEventType.get_type(event)
        if ServerEventType.is_session_event(event, type_name):
            return self._recv_session_event(event, type_name)
        elif ServerEventType.rate_limits_updated:
            return self._update_rate_limit(event)
        elif ServerEventType.is_conversation_event(event, type_name):
            return self._recv_conversation_event(event)
        elif ServerEventType.is_input_audio_event(event, type_name):
            return self._recv_input_audio_event(event)
        elif ServerEventType.is_respond_event(event, type_name):
            return self._recv_response_event(event)
        else:
            return self.recv_invalid_event(event)

    def gc(self):
        pass

    def _recv_session_event(self, event: dict, e_type: str):
        if e_type == ServerSessionCreated.type:
            obj = ServerSessionCreated(**event)
        elif e_type == ServerSessionUpdated.type:
            obj = ServerSessionUpdated(**event)
        else:
            return self.recv_invalid_event(event)
        if obj.session_id != self.session_obj.session_id:
            return self.recv_invalid_event(event)
        return self.ack_server_event(obj)

    def _recv_response_event(self, event: dict):
        pass

    def _recv_conversation_event(self, event: dict):
        pass

    def _recv_input_audio_event(self, event: dict):
        pass

    def _update_rate_limit(self, event: dict):
        pass


class ConversationState(Protocol):
    session_id: str
    conversation_id: str
    items: dict[int, ConversationItemStatus]
    responses: dict[int, ResponseBuffer]
    status: Literal["new", "created", "closed"]

    @abstractmethod
    def recv(self, event: dict):
        if ServerEventType.conversation_created.match(event):
            self.status = "created"
            return
        elif ServerEventType.conversation_item_created.match(event):
            self._update_item(event)
            return

    def _update_item(self, event: dict):
        pass


class ConversationItemStatus(Protocol):
    session_id: str
    conversation_id: str
    index: int
    item_id: str

    @abstractmethod
    def recv(self, event: dict):
        pass


class InputAudioBuffer(Protocol):
    pass


class ResponseBuffer(Protocol):
    output_items: dict[int, OutputItemBuffer]


class OutputItemBuffer(Protocol):
    pass
