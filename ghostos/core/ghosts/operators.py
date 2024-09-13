from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, ClassVar, Dict, Type
from ghostos.core.session import Event
from ghostos.core.moss.decorators import cls_definition

if TYPE_CHECKING:
    from ghostos.core.ghosts.ghost import Ghost

__all__ = ['Operator', 'EventOperator', 'get_event_operator']


@cls_definition()
class Operator(ABC):
    """
    Operating the chain of thoughts.
    You CAN NOT define operator yourself, you shall generate it by given library only.
    """

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

    def __init__(self, event: Event):
        self.event = event

    def destroy(self) -> None:
        del self.event


def get_event_operator(operators: Dict[str, Type[EventOperator]], event: Event) -> Optional[EventOperator]:
    """
    根据事件类型, 从 operators 中挑选合适的 EventOperator
    :param operators:
    :param event:
    :return:
    """
    if event.type in operators:
        return operators[event.type](event)
    if "" in operators:
        return operators[""](event)
    return None
