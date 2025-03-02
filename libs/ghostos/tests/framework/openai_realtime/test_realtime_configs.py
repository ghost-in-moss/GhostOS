from ghostos.framework.openai_realtime.configs import OpenAIRealtimeAppConf


def test_vad_session():
    conf = OpenAIRealtimeAppConf()
    session = conf.get_session_obj(vad_mode=True)
    assert session.turn_detection is not None
    session = conf.get_session_obj(vad_mode=False)
    assert session.turn_detection is None
