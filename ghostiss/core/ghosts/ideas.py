from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar, Optional, List, Union, TypedDict
from ghostiss.entity import Entity, EntityDriver, Normalized, EntityDriver, MetaFactory

if TYPE_CHECKING:
    from ghostiss.core.ghosts.ghost import Ghost, TaskCtx
    from ghostiss.core.ghosts.operators import Operator
    from ghostiss.core.ghosts.events import Event, EventLoader


class Idea(Entity, ABC):
    pass


IDEA_TYPE = TypeVar('IDEA_TYPE', bound=Idea)


class IdeaInfo(TypedDict):
    name: str
    description: str


class IdeaDriver(EntityDriver[IDEA_TYPE], ABC):

    @abstractmethod
    def on_event(
            self,
            this: IDEA_TYPE,
            ctx: "TaskCtx",
            g: "Ghost",
            e: "Event",
    ) -> Optional["Operator"]:
        pass

    @abstractmethod
    def info(self, this: IDEA_TYPE) -> IdeaInfo:
        pass

    def on_event_meta(
            self,
            this: IDEA_TYPE,
            ctx: "TaskCtx",
            g: "Ghost",
            event: Union[Normalized, Event],
    ) -> Optional["Operator"]:
        """
        from meta create event and fire it
        """
        if isinstance(event, Event):
            e = event
        else:
            e = self.event_loader(g).new_entity(event)
            if e is None:
                raise NotImplemented("todo")
        return self.on_event(this, ctx, g, e)

    def event_loader(self, g: "Ghost") -> EventLoader:
        """
        override the method to defines custom events
        """
        return EventLoader()


IDEA_OBJECT = TypeVar('IDEA_OBJECT', bound=IdeaDriver)


# --- factories --- #

class Ideas(MetaFactory[IdeaDriver], ABC):
    pass
