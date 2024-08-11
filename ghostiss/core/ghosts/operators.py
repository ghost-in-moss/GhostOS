from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ghostiss.core.ghosts.ghost import Ghost
    from ghostiss.core.session.events import Event


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
        pass


def handle_event(g: "Ghost", e: "Event") -> Optional["Operator"]:
    """
    ghost 执行事件的基本逻辑.
    """
    session = g.session
    task = session.task()
    if task.task_id != e.task_id:
        # todo: use ghostiss error
        raise AttributeError(f"event {e.task_id} does not belong to Task {task.task_id}")
    # regenerate the thought from meta
    thought = g.mindset.force_new_entity(task.meta)
    # handle event
    op = thought.on_event(g, e)
    # update the task.meta from the thought that may be changed
    task.meta = thought.to_entity_meta()
    session.update_task(task)
    # return the operator that could be None (use default operator outside)
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
        return handle_event(g, self.event)

    def destroy(self) -> None:
        del self.event
