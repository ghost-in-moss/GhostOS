from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field
from ghostiss.core.messages.message import Message


class Run(BaseModel):
    run_id: str
    locker: Optional[str] = Field(default=None)
    instructions: str
    context: List[Message]
    inputs: List[Message]
    thinks: List[Message] = Field(default_factory=list)
    python: Optional[PyContext] = Field(default=None)
    outputs: List[Message] = Field(default_factory=list)


class Runs(ABC):

    @abstractmethod
    def get_run(self, run_id: str, lock: bool = False) -> Optional[Run]:
        pass

    @abstractmethod
    def create_run(self, run: Run) -> Run:
        pass

    @abstractmethod
    def update_run(self, run: Run) -> None:
        pass


class RunsInCtx(Runs, ABC):

    @abstractmethod
    def save(self) -> None:
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass
