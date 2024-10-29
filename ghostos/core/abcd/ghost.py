from typing import Optional

from .ghostos import Conversable, Runtime, Event, Operator


class Ghost(Conversable):

    def on_event(self, runtime: Runtime, event: Event) -> Optional[Operator]:
        pass
