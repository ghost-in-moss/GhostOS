from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar, Optional, Union
from ghostiss.entity import Entity, EntityMeta, EntityFactory

if TYPE_CHECKING:
    from ghostiss.blueprint.agent import Agent
    from ghostiss.blueprint.ghosts.ghost import Ghost
    from ghostiss.blueprint.ghosts.operators import Operator
    from ghostiss.blueprint.ghosts.events import Event, EventLoader
    from ghostiss.blueprint.kernel.runtime import Task


class Mind(Entity, ABC):
    """
    与事件互动的思维状态机.
    """

    @abstractmethod
    def on_event(
            self,
            agent: "Agent",
            e: "Event",
    ) -> Optional["Operator"]:
        pass

    def create_task(self, g: "Ghost") -> "Task":
        pass

    def on_event_meta(
            self,
            agent: "Agent",
            event: Union[EntityMeta, Event],
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
        return self.on_event(agent, e)

    def event_loader(self, agent: "Agent") -> EventLoader:
        """
        override the method to defines custom events
        """
        return EventLoader()


MIND_TYPE = TypeVar("MIND_TYPE", bound=Mind)


# --- factories --- #

class Minds(EntityFactory[MIND_TYPE], ABC):
    pass


# --- default minds --- #

class Mindflow(Mind):
    pass

class MindHost(Mind):
    pass