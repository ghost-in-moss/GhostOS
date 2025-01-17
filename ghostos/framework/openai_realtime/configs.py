from typing import ClassVar, Optional
from typing_extensions import Self
from ghostos.abcd.realtime import RealtimeAppConfig
from ghostos.contracts.configs import YamlConfig
from ghostos.framework.openai_realtime.event_data_objects import SessionObject
from pydantic import BaseModel, Field

__all__ = ['OPENAI_REALTIME_DRIVER_NAME', 'OpenAIRealtimeAppConf', 'OpenAIWebsocketsConf']

OPENAI_REALTIME_DRIVER_NAME = "openai_realtime_driver"


# 拆一个 base model 方便未来做成表单.
class OpenAIWebsocketsConf(BaseModel):
    api_key: str = Field(
        default="$OPENAI_API_KEY",
        description="The OpenAI key used to authenticate with WebSockets.",
    )
    proxy: Optional[str] = Field(
        default="$OPENAI_PROXY",
        description="The proxy to connect to. only support socket v5 now",
    )
    uri: str = Field("wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17")
    close_check: float = Field(
        default=0.5,
        description="check if the connection is still going while sending event to server",
    )

    def load_from_env(self) -> Self:
        from os import environ
        copied = self.model_copy(deep=True)
        if copied.api_key and copied.api_key.startswith("$"):
            copied.api_key = environ[copied.api_key[1:]]
        if copied.proxy and copied.proxy.startswith("$"):
            key = copied.proxy[1:]
            if key in environ:
                copied.proxy = environ[key]
            else:
                copied.proxy = ""
        return copied


class OpenAIRealtimeAppConf(YamlConfig, RealtimeAppConfig):
    """
    OpenAI Realtime Beta API configuration
    """
    relative_path: ClassVar[str] = "openai_realtime_config.yml"

    ws_conf: OpenAIWebsocketsConf = Field(
        default_factory=OpenAIWebsocketsConf,
        description="OpenAI Websockets configuration",
    )
    session: SessionObject = Field(
        default_factory=SessionObject,
        description="basic session settings, if None, use openai default session",
    )
    session_created_timeout: int = Field(10, description="session created timeout")

    def get_session_obj(self, vad_mode: bool) -> SessionObject:
        """
        get session object
        :return:
        """
        session = self.session.model_copy(deep=True)
        if not vad_mode:
            session.turn_detection = None
        return session

    def driver_name(self) -> str:
        return OPENAI_REALTIME_DRIVER_NAME
