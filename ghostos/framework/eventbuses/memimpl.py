from typing import Optional, Dict, Type
from typing_extensions import Self

from ghostos.core.runtime import Event
from ghostos.core.runtime.events import EventBus
from queue import Queue, Empty
from ghostos_container import Provider, Container, BootstrapProvider
from ghostos.contracts.shutdown import Shutdown


class MemEventBusImpl(EventBus):

    def __init__(self):
        self._events: Dict[str, Event] = {}
        self._task_notification_queue = Queue()
        self._task_queues: Dict[str, Queue] = {}

    def with_process_id(self, process_id: str) -> Self:
        return self

    def clear_all(self):
        pass

    def send_event(self, e: Event, notify: bool) -> None:
        self._send_task_event(e)
        if notify:
            self.notify_task(e.task_id)

    def _send_task_event(self, e: Event) -> None:
        event_id = e.event_id
        task_id = e.task_id
        self._events[event_id] = e
        if task_id not in self._task_queues:
            self._task_queues[task_id] = Queue()
        queue = self._task_queues[task_id]
        queue.put(event_id)

    def pop_task_event(self, task_id: str) -> Optional[Event]:
        if task_id not in self._task_queues:
            return None
        queue = self._task_queues[task_id]
        try:
            event_id = queue.get_nowait()
            if event_id in self._events:
                event = self._events.get(event_id, None)
                del self._events[event_id]
                return event
            return None
        except Empty:
            return None

    def clear_task(self, task_id: str) -> None:
        if task_id in self._task_queues:
            queue = self._task_queues[task_id]
            queue.task_done()
            del self._task_queues[task_id]

    def pop_task_notification(self) -> Optional[str]:
        try:
            task_id = self._task_notification_queue.get_nowait()
            return task_id
        except Empty:
            return None

    def notify_task(self, task_id: str) -> None:
        self._task_notification_queue.put(task_id)
        self._task_notification_queue.task_done()

    def shutdown(self) -> None:
        del self._events
        del self._task_notification_queue
        del self._task_queues


class MemEventBusImplProvider(BootstrapProvider[EventBus]):
    """
    mem event bus provider
    """

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[EventBus]:
        return EventBus

    def factory(self, con: Container) -> Optional[EventBus]:
        return MemEventBusImpl()

    def bootstrap(self, container: Container) -> None:
        shutdown = container.get(Shutdown)
        if shutdown is not None:
            eventbus = container.force_fetch(EventBus)
            if isinstance(eventbus, MemEventBusImpl):
                shutdown.register(eventbus.shutdown)
