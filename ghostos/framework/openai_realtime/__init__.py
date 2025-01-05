from ghostos.abcd import Conversation
from ghostos.abcd.realtime import RealtimeApp
from ghostos.abcd.realtime import Speaker, Listener


def get_openai_realtime_app(
        conversation: Conversation,
        *,
        vad_mode: bool,
        speaker: Speaker,
        listener: Listener,
) -> RealtimeApp:
    from ghostos.framework.openai_realtime.driver import OpenAIRealtimeDriver
    from ghostos.framework.openai_realtime.app import RealtimeAppImpl
    from ghostos.framework.openai_realtime.configs import OpenAIRealtimeAppConf
    from ghostos.framework.openai_realtime.ws import OpenAIWSConnection
    from ghostos.bootstrap import get_container
    from ghostos.contracts.configs import Configs

    _container = get_container()
    _configs = _container.force_fetch(Configs)
    _conf = _configs.get(OpenAIRealtimeAppConf)
    return RealtimeAppImpl(
        conf=_conf,
        vad_mode=vad_mode,
        conversation=conversation,
        listener=listener,
        speaker=speaker,
    )
