from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ghostiss.blueprint.ghosts.ghost import Ghost, TaskCtx


class Operator(ABC):
    """
    变更上下文.
    """

    @abstractmethod
    def run(self, ctx: "TaskCtx", g: "Ghost") -> Optional["Operator"]:
        pass
