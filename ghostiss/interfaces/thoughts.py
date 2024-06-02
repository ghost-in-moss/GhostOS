from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, TypeVar, Generic

from ghostiss.meta import Meta, MetaClass
from ghostiss.messages import Message, Messenger
from ghostiss.context import Context

if TYPE_CHECKING:
    from ghostiss.interfaces.agent import Agent
    from ghostiss.interfaces.llms import Run
    from ghostiss.interfaces.kernel import Operator
    from ghostiss.interfaces.threads import ThreadRun, Inputs
    from ghostiss.interfaces.runtime import Task


class Attention(ABC):

    @abstractmethod
    def attend(self, messages: List[Message]) -> Optional["Operator"]:
        pass


class Thought(Meta, ABC):
    pass


T = TypeVar("T", bound=Thought)


class Event(ABC):
    task: Task


class TaskOverflow(Event):
    pass


class OnIntercept(Event):

    def __init__(self, task: Task, inputs: "Inputs"):
        self.task = task
        self.inputs: "Inputs" = inputs


class OnTaskCreation(Event):
    """
    task 创建.
    """

    def __init__(self, task: "Task"):
        self.task = task


class Think(Generic[T], MetaClass[T], ABC):

    @abstractmethod
    def on_event(self, ctx: Context, thought: T, agent: "Agent", event: Event) -> Optional["Operator"]:
        pass

    @abstractmethod
    def intercept(self, ctx: Context, thought: T, agent: "Agent", thread_run: "ThreadRun") -> Optional["Operator"]:
        """
        intercept 实现得好就不需要别的了.
        """
        pass

    @abstractmethod
    def fallback(self, ctx: Context, thought: T, agent: "Agent", thread_run: "ThreadRun") -> Optional["Operator"]:
        pass

    @abstractmethod
    def attentions(self, ctx: Context, thought: T) -> List[Attention]:
        pass

    @abstractmethod
    def generate_run(self, ctx: Context, thought: T, agent: "Agent", thread_run: "ThreadRun") -> Run:
        pass

    @abstractmethod
    def messenger(self, ctx: Context, thought: T, agent: "Agent") -> Messenger:
        pass


class Mindset(ABC):

    @abstractmethod
    def force_fetch(self, ctx: Context, clazz_name: str) -> Think:
        pass
