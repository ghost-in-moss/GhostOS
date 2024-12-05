from typing import Optional, ClassVar
from pydantic import Field
from ghostos.abcd.realtime import RealtimeAppConfig
from ghostos.contracts.configs import YamlConfig
from .ws import OpenAIWebsocketsConf
from .event_data_objects import SessionObject

__all__ = ['OPENAI_REALTIME_DRIVER_NAME', 'OpenAIRealtimeAppConf']

OPENAI_REALTIME_DRIVER_NAME = "openai_realtime_driver"


class OpenAIRealtimeAppConf(YamlConfig, RealtimeAppConfig):
    relative_path: ClassVar[str] = "openai_realtime_config.yml"

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

    session_created_timeout: int = Field(10)

    def driver_name(self) -> str:
        return OPENAI_REALTIME_DRIVER_NAME
