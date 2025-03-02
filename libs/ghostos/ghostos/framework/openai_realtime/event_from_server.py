import base64
from typing import List, Optional, Union, ClassVar
from typing_extensions import Self
from abc import ABC
from enum import Enum
from pydantic import BaseModel, Field
from ghostos.core.messages import Message as GhostOSMessage, MessageType
from ghostos.framework.openai_realtime.event_data_objects import (
    RateLimit, Response, MessageItem,
    DeltaIndex, ConversationObject, Error, SessionObject,
    Content,
)

__all__ = [
    'ServerEventType',
    'ServerEvent',
    # 28 server events

    'ServerError',

    # 2 session events
    'ServerSessionUpdated',
    'ServerSessionCreated',

    'ConversationCreated',

    # rate event
    'RateLimitsUpdated',

    # 4 input audio
    'InputAudioBufferSpeechStarted',
    'InputAudioBufferCommitted',
    'InputAudioBufferCleared',
    'InputAudioBufferSpeechStopped',

    # 5 conversation item events
    'ConversationItemCreated',
    'ConversationItemTruncated',
    'ConversationInputAudioTranscriptionCompleted',
    'ConversationInputAudioTranscriptionFailed',
    'ConversationItemDeleted',

    # 14 response events
    'ResponseCreated',
    'ResponseDone',

    'ResponseOutputItemAdded',
    'ResponseOutputItemDone',

    'ResponseContentPartAdded',
    'ResponseContentPartDone',
    # delta
    'ResponseAudioDelta',
    'ResponseAudioDone',

    'ResponseAudioTranscriptDelta',
    'ResponseAudioTranscriptDone',

    'ResponseTextDelta',
    'ResponseTextDone',

    'ResponseFunctionCallArgumentsDelta',
    'ResponseFunctionCallArgumentsDone',

]


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

    # 14 response events
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
        return e_type.startswith("response.")

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

    @classmethod
    def get_item_id(cls, event: dict) -> Optional[str]:
        if "item_id" in event:
            return event["item_id"]
        elif "item" in event:
            item = event['item']
            if isinstance(item, dict) and "item_id" in item:
                return item["item_id"]
        return None

    def match(self, event: dict) -> bool:
        return "type" in event and event["type"] == self.value


# ---- server side events ---- #

class ServerEvent(BaseModel, ABC):
    type: ClassVar[str]
    event_id: str = Field(description="Optional client-generated ID used to identify this event.")


class ServerError(ServerEvent):
    type: ClassVar[str] = ServerEventType.error.value
    error: Error


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
    """
    Returned when a conversation item is created.
    There are several scenarios that produce this event:

    1. The server is generating a Response,
       which if successful will produce either one or two Items,
       which will be of type message (role assistant) or type function_call.
    2. The input audio buffer has been committed,
       either by the client or the server (in server_vad mode).
       The server will take the content of the input audio buffer and add it to a new user message Item.
    3. The client has sent a conversation.item.create event to add a new Item to the Conversation.
    """
    type: ClassVar[str] = ServerEventType.conversation_item_created.value
    previous_item_id: Optional[str] = Field(None)
    item: MessageItem = Field()


class ConversationItemDeleted(ServerEvent):
    type: ClassVar[str] = ServerEventType.conversation_item_deleted.value
    item_id: str = Field("")


class ConversationInputAudioTranscriptionCompleted(ServerEvent):
    """
    This event is the output of audio transcription for user audio written to the user audio buffer.
    Transcription begins when the input audio buffer is committed by the client or server
    (in server_vad mode).
    Transcription runs asynchronously with Response creation,
    so this event may come before or after the Response events.
    Realtime API models accept audio natively,
    and thus input transcription is a separate process run on a separate ASR (Automatic Speech Recognition) model,
    currently always whisper-1.
    Thus the transcript may diverge somewhat from the model's interpretation,
    and should be treated as a rough guide.
    """
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
    """
    Returned when an earlier assistant audio message item is truncated by the client with
    a conversation.item.truncate event.
    This event is used to synchronize the server's understanding of the audio with the client's playback.
    This action will truncate the audio and remove the server-side text transcript
    to ensure there is no text in the context that hasn't been heard by the user.
    """
    type: ClassVar[str] = ServerEventType.conversation_item_truncated.value
    item_id: str = Field("")
    content_index: int = Field(default=0)
    audio_end_ms: int = Field(default=0)


class InputAudioBufferCommitted(ServerEvent):
    type: ClassVar[str] = ServerEventType.input_audio_buffer_committed.value
    previous_item_id: Optional[str] = Field(None)
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
    content_index: int = Field(0)
    output_index: int = Field(0)
    item_id: str = Field("")
    part: Content = Field(None, description="The content part that was added. shall not be None.")

    def as_message_chunk(self) -> Optional[GhostOSMessage]:
        if self.part is None:
            return None
        if self.part.transcript:
            return GhostOSMessage.new_chunk(
                msg_id=self.item_id,
                content=self.part.transcript,
            )
        elif self.part.text:
            return GhostOSMessage.new_chunk(
                msg_id=self.item_id,
                content=self.part.text,
            )
        else:
            return None


class ResponseContentPartDone(ServerEvent):
    type: ClassVar[str] = ServerEventType.response_content_part_done.value
    response_id: str = Field("")
    output_index: int = Field(0)
    item_id: str = Field("")
    part: Content = Field()

    def as_message_chunk(self) -> Optional[GhostOSMessage]:
        if self.part is None:
            return None
        if self.part.transcript:
            return GhostOSMessage.new_chunk(
                msg_id=self.item_id,
                content=self.part.transcript,
            )
        elif self.part.text:
            return GhostOSMessage.new_chunk(
                msg_id=self.item_id,
                content=self.part.text,
            )
        else:
            return None


class ResponseTextDelta(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_text_delta.value
    delta: str = Field("")

    def as_content(self) -> Content:
        return Content(
            type="text",
            text=self.delta,
        )

    def as_message_chunk(self) -> Optional[GhostOSMessage]:
        if self.delta:
            return GhostOSMessage.new_chunk(
                msg_id=self.item_id,
                content=self.delta,
            )
        return None


class ResponseTextDone(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_text_done.value
    text: str = Field("")

    def as_content(self) -> Content:
        return Content(
            type="text",
            text=self.text,
        )


class ResponseAudioTranscriptDelta(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_audio_transcript_delta.value
    delta: str = Field("")

    def as_content(self) -> Content:
        return Content(
            type="audio",
            transcript=self.delta,
        )

    def as_message_chunk(self) -> Optional[GhostOSMessage]:
        if self.delta:
            return GhostOSMessage.new_chunk(
                msg_id=self.item_id,
                content=self.delta,
            )
        return None


class ResponseAudioTranscriptDone(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_audio_transcript_done.value
    transcript: str = Field("")

    def as_content(self) -> Content:
        return Content(
            type="audio",
            transcript=self.delta,
        )


class ResponseAudioDelta(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_audio_delta.value
    delta: str = Field("")

    def get_audio_bytes(self) -> bytes:
        return base64.b64decode(self.delta)


class ResponseAudioDone(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_audio_transcript_done.value


class ResponseFunctionCallArgumentsDelta(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_function_call_arguments_delta.value
    delta: str = Field("")

    def as_message_chunk(self) -> Optional[GhostOSMessage]:
        if self.delta:
            return GhostOSMessage.new_chunk(
                typ_=MessageType.FUNCTION_CALL.value,
                msg_id=self.item_id,
                content=self.delta,
            )
        return None


class ResponseFunctionCallArgumentsDone(DeltaIndex, ServerEvent):
    type: ClassVar[str] = ServerEventType.response_function_call_arguments_done.value
    call_id: str = Field("")
    arguments: str = Field("")
    name: str = Field("")

    def as_message(self) -> GhostOSMessage:
        return GhostOSMessage.new_tail(
            msg_id=self.item_id,
            type_=MessageType.FUNCTION_CALL.value,
            name=self.name,
            content=self.arguments,
            call_id=self.call_id,
        )


class RateLimitsUpdated(ServerEvent):
    """
    Emitted at the beginning of a Response to indicate the updated rate limits.
    When a Response is created some tokens will be "reserved" for the output tokens,
    the rate limits shown here reflect that reservation,
    which is then adjusted accordingly once the Response is completed.
    """
    type: ClassVar[str] = ServerEventType.rate_limits_updated.value
    rate_limits: List[RateLimit] = Field(default_factory=list)
