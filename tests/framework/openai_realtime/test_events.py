from ghostos.framework.openai_realtime.event_data_objects import SessionObject
from ghostos.framework.openai_realtime.event_from_client import SessionUpdate


def test_session_update_event():
    session = SessionObject()
    ce = SessionUpdate(session=session)
    assert ce.session == session
