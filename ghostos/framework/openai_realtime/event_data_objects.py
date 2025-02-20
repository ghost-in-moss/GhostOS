from __future__ import annotations

import base64

from pydantic import BaseModel, Field
from typing import Optional, List, Union, Dict
from typing_extensions import Literal
from io import BytesIO
from ghostos.core.messages import (
    MessageType, Message, AudioMessage, FunctionCallMessage, FunctionCallOutputMessage,
    FunctionCaller, Role,
)
from ghostos_common.helpers import md5
from enum import Enum


class RateLimit(BaseModel):
    name: str = Field("", description="Name of the rate-limited event.", enum={"requests", "tokens"})
    limit: int = Field(0, description="The maximum allowed value for the rate limit.")
    remaining: int = Field(0, description="The remaining value before the limit is reached.")
    reset_seconds: float = Field(0.0, description="Seconds until the rate limit resets.")


class TokensDetails(BaseModel):
    cached_tokens: int = Field(default=0)
    text_tokens: int = Field(default=0)
    audio_tokens: int = Field(default=0)


class Usage(BaseModel):
    total_tokens: int = Field()
    input_tokens: int = Field()
    output_tokens: int = Field()
    input_token_details: Optional[TokensDetails] = Field(None)
    output_token_details: Optional[TokensDetails] = Field(None)


class Error(BaseModel):
    type: str = Field("")
    code: Optional[str] = Field(None)
    message: Optional[str] = Field(None)
    param: Optional[str] = Field(None)


class ResponseStatusDetails(BaseModel):
    type: str = Field("")
    reason: str = Field("")
    error: Optional[Error] = Field(None)


class Response(BaseModel):
    id: str = Field()
    object: str = Field("realtime.response")
    status: Literal["completed", "cancelled", "failed", "incomplete", "in_progress"] = Field()
    status_details: Optional[ResponseStatusDetails] = Field(None)
    output: List[MessageItem] = Field(default_factory=list)
    usage: Optional[Usage] = Field(None)


class Content(BaseModel):
    """
    The content of the message, applicable for message items.
    Message items with a role of system support only input_text content,
    message items of role user support input_text and input_audio content,
    and message items of role assistant support text content.
    """
    type: Literal["input_text", "input_audio", "text", "audio"] = Field()
    text: Optional[str] = Field(None)
    audio: Optional[str] = Field(None)
    transcript: Optional[str] = Field(None)


class MessageItem(BaseModel):
    """
    The item to add to the conversation.
    """
    id: Optional[str] = Field(None)
    type: Literal["message", "function_call", "function_call_output"] = Field("")
    status: Optional[str] = Field(None, enum={"completed", "incomplete"})
    role: Optional[str] = Field(default=None, enum={"assistant", "user", "system"})
    content: Optional[List[Content]] = Field(None)
    call_id: Optional[str] = Field(None)
    name: Optional[str] = Field(None, description="The name of the function being called (for function_call items).")
    arguments: Optional[str] = Field(None, description="The arguments of the function call (for function_call items).")
    output: Optional[str] = Field(None, description="The output of the function call (for function_call_output items).")

    @classmethod
    def from_message(cls, message: Message) -> Optional[MessageItem]:
        if message is None or not message.content:
            return None
        id_ = message.msg_id
        call_id = None
        output = None
        arguments = None
        content = None
        role = message.role
        if not role:
            role = Role.ASSISTANT.value

        if message.type == MessageType.FUNCTION_CALL.value:
            type_ = "function_call"
            call_id = message.call_id
            arguments = message.content
            role = None
        elif message.type == MessageType.FUNCTION_OUTPUT.value:
            type_ = "function_call_output"
            call_id = message.call_id
            output = message.content
            role = None
        else:

            type_ = "message"
            if role == Role.ASSISTANT.value:
                content_type = "text"
                content = [
                    Content(type=content_type, text=message.content),
                ]
            elif role == Role.USER.value:
                content_type = "input_text"
                content = [
                    Content(type=content_type, text=message.content),
                ]
            elif role == Role.SYSTEM.value:
                content_type = "input_text"
                content = [
                    Content(type=content_type, text=message.content),
                ]
            else:
                content_type = "input_text"
                content = [
                    Content(type=content_type, text=message.content),
                ]
        return cls(
            id=id_,
            type=type_,
            role=role,
            content=content,
            arguments=arguments,
            call_id=call_id,
            output=output,
        )

    @classmethod
    def from_audio_message(cls, message: Message) -> MessageItem:
        pass

    def has_audio(self) -> bool:
        if self.content and len(self.content) > 0:
            for c in self.content:
                if c.type == "input_audio":
                    return True
        return False

    def get_audio_bytes(self) -> bytes:
        buffer = BytesIO()
        for c in self.content:
            if c.audio:
                data = base64.b64decode(c.audio)
                buffer.write(data)
        return buffer.getvalue()

    def to_message_head(self) -> Message:

        if self.type == "function_call_output":
            return Message.new_head(
                typ_=MessageType.FUNCTION_OUTPUT.value,
                role=self.role or Role.ASSISTANT.value,
                content=self.output,
                msg_id=self.id,
                call_id=self.call_id,
            )
        elif self.type == "function_call":
            return Message.new_head(
                typ_=MessageType.FUNCTION_CALL.value,
                msg_id=self.id,
                role=self.role or Role.ASSISTANT.value,
                name=self.name,
                call_id=self.call_id,
                content=self.arguments,
            )
        elif self.type == "message":
            content = ""
            for c in self.content:
                if c.text:
                    content += c.text
                elif c.transcript:
                    content += c.transcript

            typ_ = MessageType.DEFAULT.value
            if self.role == Role.ASSISTANT.value:
                typ_ = MessageType.AUDIO.value

            return Message.new_head(
                typ_=typ_,
                msg_id=self.id,
                role=self.role or "",
                content=content,
            )

        else:
            return Message.new_head(
                msg_id=self.id,
                role=self.role or "",
            )

    def to_complete_message(self) -> Optional[Message]:
        if self.status == "incomplete":
            return None
        if self.type == "function_call_output":
            return FunctionCallOutputMessage(
                msg_id=self.id,
                name=self.name,
                call_id=self.call_id,
                content=self.output,
            ).to_message()
        elif self.type == "function_call":
            return FunctionCallMessage(
                msg_id=self.id,
                role=self.role or "",
                caller=FunctionCaller(
                    call_id=self.call_id,
                    name=self.name,
                    arguments=self.arguments,
                )
            ).to_message()
        elif self.type == "message":
            parsed_type = MessageType.TEXT
            if self.role == Role.ASSISTANT.value or self.has_audio():
                parsed_type = MessageType.AUDIO

            parsed_content = ""
            for c in self.content:
                if c.text:
                    parsed_content = parsed_content + c.text
                elif c.transcript:
                    parsed_content = parsed_content + c.transcript
            if not parsed_content:
                return None

            if parsed_type is MessageType.AUDIO:
                return AudioMessage(
                    msg_id=self.id,
                    role=self.role or "",
                    content=parsed_content,
                ).to_message()
            else:
                return Message.new_tail(
                    msg_id=self.id,
                    role=self.role or "",
                    content=parsed_content,
                )
        else:
            return None


class DeltaIndex(BaseModel):
    response_id: str = Field("")
    item_id: str = Field("")
    output_index: int = Field(0)
    content_index: int = Field(0)


class ConversationObject(BaseModel):
    id: str = Field("")
    object: str = Field("realtime.conversation")


class TurnDetection(BaseModel):
    type: str = Field("server_vad")
    threshold: float = Field(
        0.5,
        description="Activation threshold for VAD (0.0 to 1.0), "
                    "this defaults to 0.5. A higher threshold will require louder audio to activate the model, "
                    "and thus might perform better in noisy environments.",
    )
    prefix_padding_ms: int = Field(
        default=300,
        description="Amount of audio to include before the VAD detected speech (in milliseconds). Defaults to 300ms."
    )
    silence_duration_ms: int = Field(
        default=500,
        description="Duration of silence to detect speech stop (in milliseconds). "
                    "Defaults to 500ms. "
                    "With shorter values the model will respond more quickly, "
                    "but may jump in on short pauses from the user."
    )


class InputAudioTranscription(BaseModel):
    model: str = Field("whisper-1")


class Voice(str, Enum):
    alloy = "alloy"
    echo = "echo"
    shimmer = "shimmer"
    ash = "ash"
    ballad = "ballad"
    coral = "coral"
    sage = "sage"
    verse = "verse"


class OpenAIRealtimeModel(str, Enum):
    gpt_4o_realtime_preview_2024_10_01 = "gpt-4o-realtime-preview-2024-10-01"
    gpt_4o_mini_realtime_preview_2024_12_17 = "gpt-4o-mini-realtime-preview-2024-12-17"
    gpt_4o_realtime_preview_2024_12_17 = "gpt-4o-realtime-preview-2024-12-17"


class Tool(BaseModel):
    type: Literal["function"] = "function"
    name: str = Field()
    description: str = Field()
    parameters: Dict = Field(default_factory=dict)


class SessionObjectBase(BaseModel):
    """
    immutable configuration for the openai session object
    """
    model: OpenAIRealtimeModel = Field(OpenAIRealtimeModel.gpt_4o_realtime_preview_2024_12_17)
    modalities: List[str] = Field(default_factory=lambda: ["audio", "text"], enum={"text", "audio"})
    voice: str = Field(
        default="coral",
        description="Voice to use",
    )
    input_audio_format: str = Field(
        default="pcm16",
        enum={"pcm16", "g711_ulaw", "g711_alaw"},
        description="only support pcm16 yet",
    )
    output_audio_format: str = Field(
        default="pcm16",
        enum={"pcm16", "g711_ulaw", "g711_alaw"},
        description="only support pcm16 yet",
    )
    turn_detection: Union[TurnDetection, None] = Field(
        default_factory=TurnDetection,
        description="Configuration for turn detection. "
                    "Can be set to null to turn off. "
                    "Server VAD means that the model will detect the start and end of speech based on audio volume "
                    "and respond at the end of user speech."
    )
    input_audio_transcription: Optional[InputAudioTranscription] = Field(
        default_factory=InputAudioTranscription,
        description="Configuration for input audio transcription."
    )
    instructions: str = Field(default="", description="instructions of the session")
    tools: List[Tool] = Field(default_factory=list)
    tool_choice: str = Field(default="auto")
    temperature: float = Field(default=0.8)
    max_response_output_tokens: Union[int, Literal['inf']] = Field(default='inf')


class ResponseSettings(BaseModel):
    modalities: List[str] = Field(default_factory=lambda: ["audio", "text"], enum={"text", "audio"})
    voice: Voice = Field(
        default="coral",
        description="Voice to use",
    )
    output_audio_format: str = Field(
        default="pcm16",
        enum={"pcm16", "g711_ulaw", "g711_alaw"},
        description="only support pcm16 yet",
    )
    instructions: str = Field(default="", description="instructions of the session")
    tools: List[dict] = Field(default_factory=list)
    tool_choice: str = Field(default="auto")
    temperature: float = Field(default=0.8)

    # max_response_output_tokens: Union[int, Literal['inf']] = Field(default='inf')

    @classmethod
    def from_session(cls, session: SessionObjectBase):
        return cls(**session.model_dump())


class SessionObject(SessionObjectBase):
    """
    full data model for openai realtime-api session object
    """
    id: str = Field(default="", description="id of the session")
    object: Literal["realtime.session"] = "realtime.session"
