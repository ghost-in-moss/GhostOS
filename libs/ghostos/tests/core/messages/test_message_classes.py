from ghostos.core.messages.message_classes import ConfirmMessage
from ghostos.core.runtime.events import EventTypes


def test_confirm_message():
    e = EventTypes.INPUT.new("hello", [])
    confirm = ConfirmMessage.new(content="hello", event=e.model_dump())
    assert confirm.event is not None
    message = confirm.to_message()
    assert message.attrs is not None
    new_confirm = ConfirmMessage.from_message(message)
    assert new_confirm is not None
    assert new_confirm.model_dump() == confirm.model_dump()
