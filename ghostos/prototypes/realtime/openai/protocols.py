from typing import Self, Literal, List, Optional, Union, Dict
from enum import Enum
from ghostos.prototypes.realtime.abcd import SessionProtocol, Function
from pydantic import BaseModel, Field
from ghostos.helpers import uuid


class ServerEventType(str, Enum):
    error = "error"
    session_created = "session.created"

    @classmethod
    def get_type(cls, event: dict) -> Self:
        return cls(event["type"])


class SessionObjBase(BaseModel):
    """
    immutable configuration for the openai session object
    """
    model: str = Field("gpt-4o-realtime-preview-2024-10-01")
    modalities: List[str] = Field(default_factory=list, enum={"text", "audio"})
    voice: str = Field(default="alloy", enum={"alloy", "echo", "shimmer"})
    input_audio_format: str = Field(default="pcm16", enum={"pcm16", "g711_ulaw", "g711_alaw"})
    output_audio_format: str = Field(default="pcm16", enum={"pcm16", "g711_ulaw", "g711_alaw"})
    turn_detection: Union[Dict, None] = Field(None)


class SessionObj(SessionObjBase):
    """
    full data model for openai realtime-api session object
    """
    id: str = Field(default_factory=uuid)
    object: Literal["realtime.session"] = "realtime.session"
    tools: List[dict] = Field(default_factory=list)
    tool_choice: str = Field(default="auto")
    temperature: float = Field(default=0.8)
    max_response_output_tokens: Union[int, Literal['inf']] = Field(default='inf')

