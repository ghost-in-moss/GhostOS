from ghostos.framework.openai_realtime.configs import OpenAIRealtimeAppConf
from ghostos.framework.openai_realtime.event_data_objects import SessionObject


def test_configs_session():
    conf = OpenAIRealtimeAppConf()
    assert isinstance(conf.session, SessionObject)
