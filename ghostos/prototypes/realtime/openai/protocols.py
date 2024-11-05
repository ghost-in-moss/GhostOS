from typing import Self, Literal, List, Optional, Union, Dict, Protocol, ClassVar, Set
from abc import ABC, abstractmethod
from enum import Enum
from ghostos.prototypes.realtime.abcd import Function
from pydantic import BaseModel, Field
from ghostos.helpers import uuid


class StateName(str, Enum):
    # --- can not change
    stopped = "stopped"

    # --- blocking
    connecting = "connecting"
    session_updating = "session_updating"

    # --- interruptible
    responding = "responding"
    input_audio = "audio_input"
    listening = "listening"  # vad

    idle = "idle"

    # --- special operations allowed
    failed = "failed"  # failed but reconnect-able

    # I think this state is parallel, need test
    # creating_conversation_item = "creating_conversation_item"


class OperatorName(str, Enum):
    # --- idempotent or immediately
    stop = "stop"  # highest priority
    reconnect = "reconnect"  # second to stop

    # --- parallel actions
    text_input = "text_input"
    function_output = "function_output"

    # --- blocking
    session_update = "session_updating"

    # --- idempotent or illegal
    create_response = "create_response"
    input_audio = "input_audio"  # push-to-talk mode
    start_listening = "start_listening"  # start vad listening

    # --- immediately or illegal
    truncate_listening = "truncate_listening"  # vad only
    response_cancel = "response_cancel"


class ServerEventType(str, Enum):
    # recover-able error
    error = "error"

    # non-block inform
    session_created = "session.created"
    session_updated = "session.updated"
    conversation_created = "conversation.created"

    # streaming items

    # complete message item alignments
    conversation_item_created = "conversation.item.created"
    conversation_item_deleted = "conversation.item.deleted"
    audio_transcript_created = "conversation.item.input_audio_transcription.completed"
    audio_transcript_failed = "conversation.item.input_audio_transcription.failed"
    response_output_item_done = "response.output_item.done"

    # system
    rate_limits_updated = "rate_limits.updated"

    @classmethod
    def conversation_item_events(cls) -> List["ServerEventType"]:
        return [
            cls.conversation_item_created,
            cls.conversation_item_deleted,
            cls.audio_transcript_created,
            cls.audio_transcript_failed,
            cls.response_output_item_done,
        ]

    @classmethod
    def get_type(cls, event: dict) -> Self:
        return cls(event["type"])

    @classmethod
    def get_event_id(cls, event: dict) -> str:
        return event.get("event_id", "")

    @classmethod
    def get_response_id(cls, event: dict) -> Union[str, None]:
        if "response" in event:
            return event["response"].get("id", None)
        if "response_id" in event:
            return event["response_id"]
        return None

    def match(self, event: dict) -> bool:
        return "type" in event and event["type"] == self.value


class ClientEventType(str, Enum):
    session_update = "session.updated"


# ---- configs ---- #

class OpenAISessionObjBase(BaseModel):
    """
    immutable configuration for the openai session object
    """
    model: str = Field("gpt-4o-realtime-preview-2024-10-01")
    modalities: List[str] = Field(default_factory=list, enum={"text", "audio"})
    voice: str = Field(default="alloy", enum={"alloy", "echo", "shimmer"})
    input_audio_format: str = Field(default="pcm16", enum={"pcm16", "g711_ulaw", "g711_alaw"})
    output_audio_format: str = Field(default="pcm16", enum={"pcm16", "g711_ulaw", "g711_alaw"})
    turn_detection: Union[Dict, None] = Field(None)


class OpenAISessionObj(OpenAISessionObjBase):
    """
    full data model for openai realtime-api session object
    """
    id: str = Field(default="", description="id of the session")
    object: Literal["realtime.session"] = "realtime.session"
    tools: List[dict] = Field(default_factory=list)
    tool_choice: str = Field(default="auto")
    temperature: float = Field(default=0.8)
    max_response_output_tokens: Union[int, Literal['inf']] = Field(default='inf')

    def get_update_event(self) -> dict:
        data = self.model_dump(exclude={'id'})
        return data


# ---- server side events ---- #

class ServerEvent(BaseModel, ABC):
    event_id: str = Field(description="Optional client-generated ID used to identify this event.")
    type: str = Field(description="server event type")


class ServerSessionCreated(ServerEvent):
    session: OpenAISessionObj


# ---- client side events ---- #


class ClientEvent(BaseModel, ABC):
    type: ClassVar[str]
    event_id: Optional[str] = Field(
        default=None,
        description="Optional client-generated ID used to identify this event.",
    )

    def to_openai_event(self) -> dict:
        event_id = self.event_id
        type_ = self.type
        data = {"type": type_}
        if event_id:
            data["event_id"] = event_id
        return self._to_openai_event(data)

    @abstractmethod
    def _to_openai_event(self, data: dict) -> dict:
        pass


class ClientSessionUpdateEvent(ClientEvent):
    type = ClientEventType.session_update.value
    session: OpenAISessionObj

    def _to_openai_event(self, data: dict) -> dict:
        data['session'] = self.session.model_dump()
        return data
