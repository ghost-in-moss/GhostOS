from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar, Optional
from ghostiss.meta import Meta, MetaObject, MetaData, MetaMaker, MetaFactory

if TYPE_CHECKING:
    from ghostiss.context import Context
    from ghostiss.core.ghosts.ghost import Ghost
    from ghostiss.core.ghosts.operators import Operator
    from ghostiss.core.ghosts.events import Event


class IdeaMeta(Meta, ABC):
    pass


I = TypeVar('I', bound=IdeaMeta)


class Idea(MetaObject[I], ABC):

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def on_event(self, ctx: "Context", g: "Ghost", e: "Event") -> Optional["Operator"]:
        pass

    @abstractmethod
    def get_meta(self) -> IdeaMeta:
        pass


IDEA_TYPE = TypeVar('IDEA_TYPE', bound=Idea)


# --- factories --- #

class IdeaMaker(Generic[IDEA_TYPE], MetaMaker[IDEA_TYPE], ABC):
    pass


# --- minds --- #

class Ideas(MetaFactory[Idea], ABC):
    pass
