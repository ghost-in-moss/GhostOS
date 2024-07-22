from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Callable, List, Dict
from ghostiss.core.messages import Message, Role, DefaultTypes

if TYPE_CHECKING:
    from ghostiss.core.ghosts.ghost import Ghost
    from ghostiss.core.ghosts.events import Event
    from ghostiss.core.ghosts.actions import Action
    from ghostiss.core.runtime.tasks import Task
    from ghostiss.core.moss.moss import MOSS


class Operator(ABC):
    """
    变更上下文.
    """

    @abstractmethod
    def run(self, g: "Ghost") -> Optional["Operator"]:
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass

    def __repr__(self) -> str:
        cls = self.__class__
        module = cls.__module__
        name = cls.__name__
        return f"Operator:{module}:{name}"


def fire_event(g: "Ghost", e: "Event") -> Optional["Operator"]:
    """
    ghost 执行事件的基本逻辑.
    """
    session = g.session
    task = session.task()
    if task.task_id != e.task_id:
        g.eventbus.send_event(e)
        return None
    thought = g.thoughts.find_thought(task.thought_meta)
    op = thought.on_event(g, e)
    task.thought_meta = thought.to_entity_meta()
    session.update_task(task)
    return op


class ActionOperator(Operator):

    def __init__(self, *, action: "Action", arguments: str) -> None:
        self._action = action
        self._arguments = arguments

    def run(self, g: "Ghost") -> Optional["Operator"]:
        return self._action.act(g, self._arguments)

    def destroy(self) -> None:
        del self._action
        del self._arguments


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
