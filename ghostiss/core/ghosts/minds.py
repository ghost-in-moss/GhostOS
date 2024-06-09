from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar, Dict, List, Optional
from ghostiss.meta import Meta, MetaObject, MetaData, MetaFactory, MetaMaker
from pydantic import Field
from ghostiss.helpers import uuid

if TYPE_CHECKING:
    from ghostiss.context import Context
    from ghostiss.core.ghosts.ghost import Ghost
    from ghostiss.core.ghosts.operators import Operator
    from ghostiss.core.ghosts.events import Event, EventLoader
    from ghostiss.core.ghosts.ideas import Idea


class MindMeta(Meta, ABC):
    """
    完全配置化的 Mind 定义.
    """
    pass


M = TypeVar("M", bound=MindMeta)


class Mind(MetaObject[M], ABC):
    """
    基于 MindMeta 驱动的 Mind 实例.
    """

    @abstractmethod
    def ideas(self, g: "Ghost") -> List[str]:
        pass

    @abstractmethod
    def get_node(self, g: 'Ghost', name: str) -> Optional[Idea]:
        pass

    @abstractmethod
    def event_loader(self, g: "Ghost") -> EventLoader:
        pass

    def on_event_meta(self, ctx: "Context", g: "Ghost", event: MetaData) -> "Operator":
        e = self.event_loader(g).meta_make(event)
        if e is None:
            raise NotImplemented("todo")
        return self.on_event(ctx, g, e)

    @abstractmethod
    def on_event(self, ctx: "Context", g: "Ghost", e: "Event") -> "Operator":
        pass


MIND_TYPE = TypeVar('MIND_TYPE', bound=Mind)


# --- factories --- #


class MindMaker(Generic[MIND_TYPE], MetaMaker[MIND_TYPE], ABC):
    pass


class Minds(MetaFactory[Mind], ABC):
    pass
