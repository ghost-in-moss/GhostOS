from ghostos.framework.openai_realtime.configs import OpenAIRealtimeAppConf
from ghostos.framework.openai_realtime.event_data_objects import SessionObject, MessageItem
from ghostos.core.messages.message_classes import FunctionCallMessage


def test_configs_session():
    conf = OpenAIRealtimeAppConf()
    assert isinstance(conf.session, SessionObject)


def test_message_item():
    item = MessageItem(id='item_Agblchy3WGzjwTH8jOMfn', type='function_call', status='completed', role=None,
                       content=None,
                       call_id='call_6Bp2ZuJoFu1NI7fI', name='moss',
                       arguments='{"code":"def run(moss: Moss):\\n    moss.body.new_move(True).spin(360, 1)\\n"}',
                       output=None)
    head = item.to_message_head()
    assert head.name == "moss"
    complete = item.to_complete_message()
    assert complete.name == "moss"
    call = FunctionCallMessage.from_message(complete)
    assert call.caller.name == "moss"
