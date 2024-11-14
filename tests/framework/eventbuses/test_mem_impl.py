from ghostos.framework.eventbuses.memimpl import MemEventBusImpl
from ghostos.core.runtime.events import EventTypes


def test_mem_impl_send_pop_event():
    bus = MemEventBusImpl()
    e = EventTypes.INPUT.new("foo", [])
    bus.send_event(e, notify=True)
    task_id = bus.pop_task_notification()
    assert task_id is not None
    assert task_id == e.task_id
    popped = bus.pop_task_event(task_id=task_id)
    assert popped is e
