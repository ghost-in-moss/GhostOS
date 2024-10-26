from typing import Optional
from pydantic import BaseModel, Field
from .ws import OpenAIWebsocketsConf
from .protocols import OpenAISessionObj


class AgentConf(BaseModel):
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
    session: Optional[OpenAISessionObj] = Field(
        default=None,
        description="basic session settings, if None, use openai default session",
    )


