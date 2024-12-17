from typing import ClassVar
from pydantic import Field
from ghostos.abcd.realtime import RealtimeAppConfig
from ghostos.contracts.configs import YamlConfig
from ghostos.framework.openai_realtime.ws import OpenAIWebsocketsConf
from ghostos.framework.openai_realtime.event_data_objects import SessionObject

__all__ = ['OPENAI_REALTIME_DRIVER_NAME', 'OpenAIRealtimeAppConf']

OPENAI_REALTIME_DRIVER_NAME = "openai_realtime_driver"


class OpenAIRealtimeAppConf(YamlConfig, RealtimeAppConfig):
    """
    configuration
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
