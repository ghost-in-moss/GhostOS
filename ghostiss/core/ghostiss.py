from typing import TYPE_CHECKING, List, Optional, Union
from abc import ABC, abstractmethod
from ghostiss.entity import Normalized
from ghostiss.core.messages import Message, Retriever
from pydantic import BaseModel, Field
if TYPE_CHECKING:
    from ghostiss.core.ghosts.ghost import Ghost, GhostMeta


class Inputs(BaseModel):
    id: str = Field(default="")
    task_id: Optional[str] = Field(default=None)
    mind_id: Optional[str] = Field(default=None)
    idea_id: Optional[str] = Field(default=None)
    context: Optional[Message] = Field(default=None)
    message: List[Message]


class GhostInShellSystem(ABC):

    def send(self, ghost: Union[Normalized, "GhostMeta"], inputs: Inputs) -> Retriever:
        pass

    def background_run_ghosts(self) -> None:
        pass


class Ghostiss(GhostInShellSystem):
    """
    简写. 浪费一下性能.
    """
    pass
