from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from ghostiss.core.ghosts.ghost import Ghost
    from ghostiss.core.runtime.tasks import Task


class Operator(ABC):
    """
    变更上下文.
    """

    @abstractmethod
    def run(self, g: "Ghost", t: "Task") -> Optional["Operator"]:
        pass


class FunctionOperator(Operator):
    """
    闭包的 adapter.
    """

    def __init__(self, func: Callable[["Ghost", "Task"], Optional[Operator]]):
        self._func = func

    def run(self, g: "Ghost", t: "Task") -> Optional["Operator"]:
        return self._func(g, t)


class MOSSOperator(Operator):
    """
    一种可能性设想.
    """

    def __init__(self, code: str):
        self._code = code

    def run(self, g: "Ghost", t: "Task") -> Optional["Operator"]:
        moss = g.moss().with_vars(g, t)
        # 先这么想一下. 思考下这么搞的可能性.
        op = moss(code=self._code, target="main", args=['os'])
        return op


