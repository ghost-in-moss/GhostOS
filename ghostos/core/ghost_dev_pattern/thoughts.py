from abc import ABC, abstractmethod
from typing import Protocol, Self, Optional, Union, Type, TypeVar, Any, Dict, TypedDict
from typing_extensions import Required
from enum import Enum
from ghostos.common import Serializable
from ghostos.core.moss import Moss


class Thought(Serializable, Protocol):
    """
    Thought describe a stateful
    """
    name: str
    purpose: str
    task: Task
    status: str
    status_reason: str
    created: float
    updated: float


class ThoughtStatus(str, Enum):
    NEW = "new"
    PENDING = "pending"
    RUNNING = "running"
    SLEEPING = "sleeping"
    DONE = "done"
    CANCELLED = "cancelled"
    ABORTED = "aborted"


T = TypeVar("T")


class Thoughts(ABC):

    @abstractmethod
    def get(self, name: str) -> Thought:
        pass

    @abstractmethod
    def create(self, *task: Task) -> Thought:
        pass

    @abstractmethod
    def update(self, *task: Task) -> Thought:
        pass

    @abstractmethod
    def delete(self, *task: Task) -> None:
        pass

    @abstractmethod
    def cancel(self, name: str, reason: str) -> None:
        pass

    @abstractmethod
    def send(self, name: str, *messages: str) -> None:
        pass
