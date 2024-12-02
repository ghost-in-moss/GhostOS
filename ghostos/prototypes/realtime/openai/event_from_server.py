from typing import Self, Literal, List, Optional, Union, Dict, Protocol, ClassVar, Set
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel, Field
from .event_data_objects import (
    RateLimit, Response, MessageItem, Content, DeltaIndex, ConversationObject, Error, SessionObject,
)


# class StateName(str, Enum):
#     # --- can not change
#     stopped = "stopped"
#
#     # --- blocking
#     connecting = "connecting"
#     session_updating = "session_updating"
#
#     # --- interruptible
#     responding = "responding"
#     input_audio = "audio_input"
#     listening = "listening"  # vad
#
#     idle = "idle"
#
#     # --- special operations allowed
#     failed = "failed"  # failed but reconnect-able
#
#     # I think this state is parallel, need test
#     # creating_conversation_item = "creating_conversation_item"
#
#
# class OperatorName(str, Enum):
#     # --- idempotent or immediately
#     stop = "stop"  # highest priority
#     reconnect = "reconnect"  # second to stop
#
#     # --- parallel actions
#     text_input = "text_input"
#     function_output = "function_output"
#
#     # --- blocking
#     session_update = "session_updating"
#
#     # --- idempotent or illegal
#     create_response = "create_response"
#     input_audio = "input_audio"  # push-to-talk mode
#     start_listening = "start_listening"  # start vad listening
#
#     # --- immediately or illegal
#     truncate_listening = "truncate_listening"  # vad only
#     response_cancel = "response_cancel"
#

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

    conversation_item_input_audio_transcription_completed = "conversation.item.input_audio_transcription.completed"
    conversation_item_input_audio_transcription_failed = "conversation.item.input_audio_transcription.failed"

    conversation_item_truncated = "conversation.item.truncated"
    conversation_item_deleted = "conversation.item.deleted"

    input_audio_buffer_committed = "input_audio_buffer.committed"
    input_audio_buffer_cleared = "input_audio_buffer.cleared"

    input_audio_buffer_speech_started = "input_audio_buffer.speech_started"
    input_audio_buffer_speech_stopped = "input_audio_buffer.speech_stopped"

    response_created = "response.created"
    response_done = "response.done"

    response_output_item_added = "response.output_item.added"
    response_output_item_done = "response.output_item.done"
    response_content_part_added = "response.content_part.added"
    response_content_part_done = "response.content_part.done"
    response_text_delta = "response.text.delta"
    response_text_done = "response.text.done"
    response_audio_transcript_delta = "response.audio_transcript.delta"
    response_audio_transcript_done = "response.audio_transcript.done"
    response_audio_delta = "response.audio.delta"
    response_audio_done = "response.audio.done"
    response_function_call_arguments_delta = "response.function_call_arguments.delta"
    response_function_call_arguments_done = "response.function_call_arguments.done"

    # system
    rate_limits_updated = "rate_limits.updated"

    @classmethod
    def get_type(cls, event: dict) -> Self:
        return cls(event.get("type", ""))

    @classmethod
    def is_session_event(cls, event: dict, e_type: Optional[str] = None) -> bool:
        if e_type is None:
            e_type = event.get("type", "")
        return e_type.startswith("session.")

    @classmethod
    def is_input_audio_event(cls, event: dict, e_type: Optional[str] = None) -> bool:
        if e_type is None:
            e_type = event.get("type", "")
        return e_type.startswith("input_audio_buffer.")

    @classmethod
    def is_respond_event(cls, event: dict, e_type: Optional[str] = None) -> bool:
        if e_type is None:
            e_type = event.get("type", "")
        return e_type.startswith("conversation.")

    @classmethod
    def is_conversation_event(cls, event: dict, e_type: Optional[str] = None) -> bool:
        if e_type is None:
            e_type = event.get("type", "")
        return e_type.startswith("conversation.")

    @classmethod
    def is_conversation_item_event(cls, event: dict, e_type: Optional[str] = None) -> bool:
        if e_type is None:
            e_type = event.get("type", "")
        return e_type.startswith("conversation.item")

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


# ---- server side events ---- #

class ServerEvent(BaseModel, ABC):
    type: ClassVar[str]
    event_id: str = Field(description="Optional client-generated ID used to identify this event.")


class ServerSessionCreated(ServerEvent):
    type: ClassVar[str] = ServerEventType.session_created.value
    session: SessionObject


class ServerSessionUpdated(ServerEvent):
    type: ClassVar[str] = ServerEventType.session_updated.value
    session: SessionObject


class ConversationCreated(ServerEvent):
    type: ClassVar[str] = ServerEventType.conversation_created.value
    conversation: ConversationObject


class ConversationItemCreated(ServerEvent):
    type: ClassVar[str] = ServerEventType.conversation_item_created.value
    previous_item_id: str = Field("")
    item: MessageItem = Field()


class ConversationItemDeleted(ServerEvent):
    type: ClassVar[str] = ServerEventType.conversation_item_deleted.value
    item_id: str = Field("")


class ConversationInputAudioTranscriptionCompleted(ServerEvent):
    type: ClassVar[str] = ServerEventType.conversation_item_input_audio_transcription_completed.value
    item_id: str = Field("")
    content_index: int = Field(default=0)
    transcript: str = Field(default="")


class ConversationInputAudioTranscriptionFailed(ServerEvent):
    type: ClassVar[str] = ServerEventType.conversation_item_input_audio_transcription_failed.value
    item_id: str = Field("")
    content_index: int = Field(default=0)
    error: Error = Field()


class ConversationItemTruncated(ServerEvent):
    type: ClassVar[str] = ServerEventType.conversation_item_truncated.value
    item_id: str = Field("")
    content_index: int = Field(default=0)
    audio_end_ms: int = Field(default=0)


class InputAudioBufferCommitted(ServerEvent):
    type: ClassVar[str] = ServerEventType.input_audio_buffer_committed.value
    previous_item_id: str = Field("")
    item_id: str = Field("")


class InputAudioBufferSpeechStarted(ServerEvent):
    type: ClassVar[str] = ServerEventType.input_audio_buffer_speech_started.value
    audio_start_ms: int = Field(default=0)
    item_id: str = Field("")


class InputAudioBufferSpeechStopped(ServerEvent):
    type: ClassVar[str] = ServerEventType.input_audio_buffer_speech_stopped.value
    audio_end_ms: int = Field(default=0)
    item_id: str = Field("")


class InputAudioBufferCleared(ServerEvent):
    type: ClassVar[str] = ServerEventType.input_audio_buffer_cleared.value


class ResponseCreated(ServerEvent):
    type: ClassVar[str] = ServerEventType.response_created.value
    response: Response = Field()


class ResponseDone(ServerEvent):
    type: ClassVar[str] = ServerEventType.response_done.value
    response: Response = Field()


class ResponseOutputItemAdded(ServerEvent):
    type: ClassVar[str] = ServerEventType.response_output_item_added.value
    response_id: str = Field("")
    output_index: int = Field(0)
    item: MessageItem = Field()


class ResponseOutputItemDone(ServerEvent):
    type: ClassVar[str] = ServerEventType.response_output_item_done.value
    response_id: str = Field("")
    output_index: int = Field(0)
    item: MessageItem = Field()


class ResponseContentPartAdded(ServerEvent):
    type: ClassVar[str] = ServerEventType.response_content_part_added.value
    response_id: str = Field("")
    output_index: int = Field(0)
    item_id: str = Field("")
    part: Content = Field()


class ResponseContentPartDone(ServerEvent):
    type: ClassVar[str] = ServerEventType.response_content_part_done.value
    response_id: str = Field("")
    output_index: int = Field(0)
    item_id: str = Field("")
    part: Content = Field()


class ResponseTextDelta(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_text_delta.value
    delta: str = Field("")


class ResponseTextDone(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_text_done.value
    text: str = Field("")


class ResponseAudioTranscriptDelta(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_audio_transcript_delta.value
    delta: str = Field("")


class ResponseAudioTranscriptDone(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_audio_transcript_done.value
    transcript: str = Field("")


class ResponseAudioDelta(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_audio_delta.value
    delta: str = Field("")


class ResponseAudioDone(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_audio_transcript_done.value


class ResponseFunctionCallArgumentsDelta(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_function_call_arguments_delta.value
    delta: str = Field("")


class ResponseFunctionCallArgumentsDone(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_function_call_arguments_done.value
    call_id: str = Field("")
    arguments: str = Field("")


class RateLimitsUpdated(ServerEvent):
    """
    Emitted at the beginning of a Response to indicate the updated rate limits.
    When a Response is created some tokens will be "reserved" for the output tokens,
    the rate limits shown here reflect that reservation,
    which is then adjusted accordingly once the Response is completed.
    """
    type: ClassVar[str] = ServerEventType.rate_limits_updated.value
    rate_limits: List[RateLimit] = Field(default_factory=list)
