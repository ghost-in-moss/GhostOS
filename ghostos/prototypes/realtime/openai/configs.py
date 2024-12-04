from typing import Optional, Literal
from pydantic import BaseModel, Field
from .ws import OpenAIWebsocketsConf
from .event_data_objects import SessionObject


class OpenAIRealtimeConf(BaseModel):
    name: str = Field(
        description="Name of the agent",
    )
    description: str = Field(
        description="Description of the agent",
    )
    ws_conf: OpenAIWebsocketsConf = Field(
        default_factory=OpenAIWebsocketsConf,
        description="OpenAI Websockets configuration",
    )
    session: Optional[SessionObject] = Field(
        default=None,
        description="basic session settings, if None, use openai default session",
    )
    start_mode: Literal["listening", "idle"] = Field("idle")

    session_created_timeout: int = Field(10)
