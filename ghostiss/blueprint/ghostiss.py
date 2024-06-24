from typing import TYPE_CHECKING, List, Optional, Union
from abc import ABC
from ghostiss.entity import EntityMeta
from ghostiss.blueprint.messages import Message, Retriever
from pydantic import BaseModel, Field
if TYPE_CHECKING:
    from ghostiss.blueprint.agents.ghost import GhostMeta


class Inputs(BaseModel):
    id: str = Field(default="")
    task_id: Optional[str] = Field(default=None)
    mind_id: Optional[str] = Field(default=None)
    idea_id: Optional[str] = Field(default=None)
    context: Optional[Message] = Field(default=None)
    message: List[Message]


class GhostInShellSystem(ABC):

    def send(self, ghost: Union[EntityMeta, "GhostMeta"], inputs: Inputs) -> Retriever:
        pass

    def background_run_ghosts(self) -> None:
        pass


class Ghostiss(GhostInShellSystem):
    """
    简写. 浪费一下性能.
    """
    pass
