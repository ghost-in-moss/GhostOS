from __future__ import annotations

from typing import List, Dict, Iterator, ClassVar, TYPE_CHECKING, Type
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

from .messages import Message
from .kernel import Kernel, Operator


# --- default events for thought --- #

class Event(ABC, BaseModel):
    """
    Ghost 的事件体系. 不同层的事件体系处理逻辑不一样.
    """
    name: ClassVar[str] = ""


class OnInput(Event):
    """
    normal message input
    """
    name: ClassVar[str] = "on_message"
    message: Message = Field(default_factory=Message, description="request message")


class OnEnter(Event):
    """
    enter a thought
    """
    name: ClassVar[str] = "on_enter"


class OnCancel(Event):
    """
    cancel or quit current thought
    """
    name: ClassVar[str] = "on_cancel"


class OnExit(Event):
    """
    quit a thought and do something necessary
    """


class OnError(Event):
    """
    some error occur
    """
    name: ClassVar[str] = "on_exit"


# --- thoughts --- #


class Thought(ABC):
    """
    思维能力的定义.
    """

    def name(self) -> str:
        """
        name of the thought, that should always be the class name
        """
        return "{module}::{clazz}".format(
            module=type(self).__module__,
            clazz=type(self).__name__,
        )

    def desc(self) -> str:
        """
        description of the thought
        """
        return type(self).__doc__

    @abstractmethod
    def on_event(self, k: Kernel, e: Event) -> Operator:
        """
        handle event.
        """
        pass
