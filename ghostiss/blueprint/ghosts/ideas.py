from abc import ABC, abstractmethod
from typing import List, NamedTuple

from pydantic import BaseModel, Field

from ghostiss.blueprint.messages.message import Message, Future
from ghostiss.blueprint.agent import Agent


class Run(BaseModel):
    id: str
    history: List[Message] = Field(default_factory=list)
    input: List[Message] = Field(default_factory=list)
    appending: List[Message] = Field(default_factory=list)


class Ran(NamedTuple):
    outputs: List[Message]
    callers: List[Future]


class Idea(ABC):

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def run(self, agent: Agent, run: Run) -> Ran:
        pass
