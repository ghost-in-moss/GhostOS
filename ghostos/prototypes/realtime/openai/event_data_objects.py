from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Union


class RateLimit(BaseModel):
    name: str = Field()
    limit: int = Field()
    remaining: int = Field()
    reset_seconds: float = Field()


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
    status: Literal["completed", "cancelled", "failed", "incomplete"] = Field()
    status_details: Optional[ResponseStatusDetails] = Field(None)
    output: List[Dict] = Field(default_factory=list)
    usage: Optional[Usage] = Field(None)


class Content(BaseModel):
    """
    The content of the message, applicable for message items.
    Message items with a role of system support only input_text content,
    message items of role user support input_text and input_audio content,
    and message items of role assistant support text content.
    """
    type: Literal["input_text", "input_audio", "text"] = Field()
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
    call_id: Optional[str] = Field(None)
    name: Optional[str] = Field(None, description="The name of the function being called (for function_call items).")
    arguments: Optional[str] = Field(None, description="The arguments of the function call (for function_call items).")
    output: Optional[str] = Field(None, description="The output of the function call (for function_call_output items).")


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
    tools: List[dict] = Field(default_factory=list)
    tool_choice: str = Field(default="auto")
    temperature: float = Field(default=0.8)
    max_response_output_tokens: Union[int, Literal['inf']] = Field(default='inf')

    def get_update_event(self) -> dict:
        data = self.model_dump(exclude={'id'})
        return data
