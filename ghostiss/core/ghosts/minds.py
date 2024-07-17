from typing import List, Optional, Union, AnyStr
from abc import ABC, abstractmethod
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.thoughts import Thought
from ghostiss.core.messages.message import Message, MessageClass

MessageType = Union[Message, MessageClass, AnyStr]


class MultiTasks(ABC):

    @abstractmethod
    def create_tasks(self, *thoughts: Thought) -> Operator:
        pass

    @abstractmethod
    def inform_task(self, name: str, *messages: MessageType) -> Operator:
        pass

    @abstractmethod
    def cancel_task(self, name: str, reason: str) -> Operator:
        pass


class TaskManager(ABC):

    @abstractmethod
    def fork(self, *quests: Optional[MessageType]) -> Operator:
        pass

    @abstractmethod
    def waits(self, *messages: MessageType) -> Operator:
        pass

    @abstractmethod
    def finish(self, *messages: MessageType) -> Operator:
        pass

    @abstractmethod
    def fail(self, reason: List[MessageType]) -> Operator:
        pass

    # @abstractmethod
    # def yield_to(self, thought: Thought) -> Operator:
    #     pass
    #
    # @abstractmethod
    # def sleep(self, seconds: float) -> Operator:
    #     pass

    @abstractmethod
    def quit(self, reason: List[MessageType]) -> Operator:
        pass


class Mindflow(ABC):

    @abstractmethod
    def next_step(self, step_name: str) -> Operator:
        pass

    @abstractmethod
    def done(self, *reason: MessageType) -> Operator:
        pass

