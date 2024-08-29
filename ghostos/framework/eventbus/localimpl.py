from typing import Optional

from ghostos.core.session import Event
from ghostos.core.session.events import EventBus


class LocalEventBusImpl(EventBus):

    def with_namespace(self, namespace: str) -> "EventBus":
        pass

    def send_event(self, e: Event, notify: bool) -> None:
        pass

    def pop_task_event(self, task_id: str) -> Optional[Event]:
        pass

    def pop_task_notification(self) -> Optional[str]:
        pass

    def notify_task(self, task_id: str) -> None:
        pass