from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ghostiss.context import Context
    from ghostiss.core.ghosts.ghost import Ghost


class Operator(ABC):
    """
    变更上下文.
    """

    @abstractmethod
    def run(self, ctx: "Context", g: "Ghost") -> Optional["Operator"]:
        pass


class Operations(ABC):
    pass
