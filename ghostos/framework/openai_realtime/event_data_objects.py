from __future__ import annotations

import base64

from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Union
from io import BytesIO
from ghostos.core.messages import (
    MessageType, Message, AudioMessage, FunctionCallMessage, FunctionCallOutputMessage,
    Caller, Role,
)


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
    code: str = Field("")
    message: str = Field("")
    param: str = Field("")


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
    text: str = Field("")
    audio: str = Field("")
    transcript: str = Field("")


class MessageItem(BaseModel):
    """
    The item to add to the conversation.
    """
    id: str = Field()
    type: Literal["message", "function_call", "function_call_output"] = Field("")
    status: Optional[str] = Field(None, enum={"completed", "incomplete"})
    role: Optional[str] = Field(None, enum={"assistant", "user", "system"})
    content: Optional[List[Content]] = Field(default_factory=None)
    call_id: Optional[str] = Field(None)
    name: Optional[str] = Field(None, description="The name of the function being called (for function_call items).")
    arguments: Optional[str] = Field(None, description="The arguments of the function call (for function_call items).")
    output: Optional[str] = Field(None, description="The output of the function call (for function_call_output items).")

    @classmethod
    def from_message(cls, message: Message) -> Optional[MessageItem]:
        id_ = message.msg_id
        call_id = None
        output = None
        arguments = None
        content = None
        role = message.role
        if message.type == MessageType.FUNCTION_CALL.value:
            type_ = "function_call"
            call_id = message.call_id
            arguments = message.content
        elif message.type == MessageType.FUNCTION_OUTPUT.value:
            type_ = "function_call_output"
            call_id = message.call_id
            output = message.content
        else:
            if not message.content:
                return None

            type_ = "message"
            if role == Role.ASSISTANT.value:
                content_type = "text"
            elif role == Role.USER.value:
                content_type = "input_text"
            elif role == Role.SYSTEM.value:
                content_type = "input_text"
            else:
                content_type = "input_text"

            content = [
                Content(type=content_type, text=message.content),
            ]
        return cls(
            id=id_,
            type=type_,
            content=content,
            arguments=arguments,
            call_id=call_id,
            output=output,
        )

    @classmethod
    def from_audio_message(cls, message: Message) -> MessageItem:
        pass

    def has_audio(self) -> bool:
        if len(self.content) > 0:
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

    def to_message_head(self) -> Optional[Message]:

        if self.type == "function_call_output":
            return Message.new_head(
                typ_=MessageType.FUNCTION_OUTPUT.value,
                role=self.role,
                content=self.output,
                msg_id=self.id,
                call_id=self.call_id,
            )
        elif self.type == "function_call":
            return Message.new_head(
                typ_=MessageType.FUNCTION_CALL.value,
                role=self.role,
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
            if not content:
                return None

            typ_ = MessageType.DEFAULT.value
            if self.role == Role.ASSISTANT.value:
                typ_ = MessageType.AUDIO.value

            return Message.new_head(
                typ_=typ_,
                role=self.role,
                content=content,
            )

        else:
            return None

    def to_complete_message(self) -> Optional[Message]:
        if self.status == "incomplete":
            return None
        if self.type == "function_call_output":
            return FunctionCallOutputMessage(
                msg_id=self.id,
                name=self.name,
                call_id=self.call_id,
                content=self.output,
            )
        elif self.type == "function_call":
            return FunctionCallMessage(
                msg_id=self.id,
                role=self.role or "",
                caller=Caller(
                    id=self.call_id,
                    name=self.name,
                    arguments=self.arguments,
                )
            )
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

            if parsed_type is MessageType.AUDIO:
                return AudioMessage(
                    msg_id=self.id,
                    content=parsed_content,
                )
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


class SessionObjectBase(BaseModel):
    """
    immutable configuration for the openai session object
    """
    model: str = Field("gpt-4o-realtime-preview-2024-10-01")
    modalities: List[str] = Field(default_factory=list, enum={"text", "audio"})
    voice: str = Field(default="alloy", enum={"alloy", "echo", "shimmer"})
    input_audio_format: str = Field(default="pcm16", enum={"pcm16", "g711_ulaw", "g711_alaw"})
    output_audio_format: str = Field(default="pcm16", enum={"pcm16", "g711_ulaw", "g711_alaw"})
    turn_detection: Union[Dict, None] = Field(None)


class SessionObject(SessionObjectBase):
    """
    full data model for openai realtime-api session object
    """
    id: str = Field(default="", description="id of the session")
    object: Literal["realtime.session"] = "realtime.session"
    instructions: str = Field(default="", description="instructions of the session")
    tools: List[dict] = Field(default_factory=list)
    tool_choice: str = Field(default="auto")
    temperature: float = Field(default=0.8)
    max_response_output_tokens: Union[int, Literal['inf']] = Field(default='inf')
