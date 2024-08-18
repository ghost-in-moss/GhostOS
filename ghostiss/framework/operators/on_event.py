from typing import ClassVar, Optional
from ghostiss.core.ghosts import EventOperator, Ghost, Operator
from ghostiss.core.session import Event


class OnEventOperator(EventOperator):
    event_type: ClassVar[str] = ""

    def __init__(self, event: Event):
        self.event = event

    @classmethod
    def new(cls, event: Event) -> "EventOperator":
        return cls(event)

    def run(self, g: "Ghost") -> Optional["Operator"]:
        pass

    def destroy(self) -> None:
        del self.event
