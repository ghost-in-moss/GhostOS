from typing import Optional

from ghostos.abcd import Conversation
from ghostos.abcd.realtime import RealtimeDriver, C, Listener, Speaker, RealtimeApp
from ghostos.framework.openai_realtime.configs import OPENAI_REALTIME_DRIVER_NAME, OpenAIRealtimeAppConf
from ghostos.framework.openai_realtime.app import RealtimeAppImpl

__all__ = ['OpenAIRealtimeDriver']


class OpenAIRealtimeDriver(RealtimeDriver[OpenAIRealtimeAppConf]):

    def driver_name(self) -> str:
        return OPENAI_REALTIME_DRIVER_NAME

    def create(
            self,
            config: OpenAIRealtimeAppConf,
            conversation: Conversation,
            listener: Optional[Listener] = None,
            speaker: Optional[Speaker] = None,
    ) -> RealtimeApp:
        return RealtimeAppImpl(
            config,
            conversation,
            listener,
            speaker,
        )