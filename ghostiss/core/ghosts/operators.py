from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, ClassVar, Dict, Type
from ghostiss.core.session import Event

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


class EventOperator(Operator, ABC):
    """
    处理指定事件的 Operator. 主要是做状态检查相关的状态机逻辑.
    """
    event_type: ClassVar[str] = ""
    """对齐 Event.type"""

    @classmethod
    @abstractmethod
    def new(cls, event: Event) -> "EventOperator":
        """
        """
        pass


def get_event_operator(operators: Dict[str, Type[EventOperator]], event: Event) -> Optional[EventOperator]:
    """
    根据事件类型, 从 operators 中挑选合适的 EventOperator
    :param operators:
    :param event:
    :return:
    """
    if event.type in operators:
        return operators[event.type].new(event)
    if "" in operators:
        return operators[""].new(event)
    return None
