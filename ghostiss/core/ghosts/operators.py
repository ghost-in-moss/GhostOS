from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
from ghostiss.core.moss.exports import Exporter

if TYPE_CHECKING:
    from ghostiss.core.ghosts.ghost import Ghost
    from ghostiss.core.ghosts.events import Event


class Operator(ABC):
    """系统运行时产生的算子, 会在外层运行. 只允许通过已有的系统函数生成, 不允许临时实现."""

    @abstractmethod
    def run(self, g: "Ghost") -> Optional["Operator"]:
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass


def fire_event(g: "Ghost", e: "Event") -> Optional["Operator"]:
    """
    ghost 执行事件的基本逻辑.
    """
    session = g.session
    task = session.task()
    if task.task_id != e.task_id:
        g.eventbus.send_event(e)
        return None
    thought = g.thoughts.new_thought(task.thought_meta)
    op = thought.on_event(g, e)
    task.thought_meta = thought.to_entity_meta()
    session.update_task(task)
    return op


#
# class ActionOperator(Operator):
#
#     def __init__(self, *, action: "Action", arguments: str) -> None:
#         self._action = action
#         self._arguments = arguments
#
#     def run(self, g: "Ghost") -> Optional["Operator"]:
#         return self._action.act(g, self._arguments)
#
#     def destroy(self) -> None:
#         del self._action
#         del self._arguments
#

class EventOperator(Operator):
    """
    通过 operator 将一个事件放到外面去.
    只是尝试一下.
    """

    def __init__(self, event: "Event"):
        self.event = event

    def run(self, g: "Ghost") -> Optional["Operator"]:
        return fire_event(g, self.event)

    def destroy(self) -> None:
        del self.event


class FinishOperator(Operator):
    pass


class WaitOperator(Operator):
    pass


EXPORTS = Exporter(). \
    with_itf(Operator)
