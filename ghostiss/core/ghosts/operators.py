from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ghostiss.core.ghosts.ghost import Ghost


class Operator(ABC):
    """系统运行时产生的算子, 会在外层运行. 只允许通过已有的系统函数生成, 不应该临时实现."""

    @abstractmethod
    def run(self, g: "Ghost") -> Optional["Operator"]:
        """
        结合 ghost 运行, 并生成下一个算子. 当下一个算子为 None 的时候, 终止流程.
        :param g: ghost instance from the task
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        主动垃圾回收.
        """
        pass


class FinishOperator(Operator):
    pass

class AwaitOperator(Operator):
    pass