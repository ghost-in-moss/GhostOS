from __future__ import annotations
from typing import List, Optional
from abc import ABC

from ghostiss.abc import Identifier
from ghostiss.container import Container
from ghostiss.core.ghosts import Ghost
from ghostiss.core.ghosts.thoughts import Thought
from pydantic import BaseModel, Field

from ghostiss.entity import EntityMeta
from ghostiss.core.moss.exports import Exporter


class FlowThoughtNode(BaseModel):
    """
    useful to define a flowchart node with edges.
    thought in the node will determine which edge shall go next.
    if no edges given, thought shall choose to finish or fail the task
    """
    name: str = Field(description="name of the node, useful to specific a node")
    instruction: str = Field(description="specific instruction for the node, including what should do and what next")
    edges: List[str] = Field(
        description="list of node names for current node to choose as next step, when current node is done",
    )
    thought: Thought = Field(description="the thought that responsible for the node")


class FileThought(Thought, BaseModel):
    """
    a thought that create a task about the file.
    can read a file and does many things such as summary, modify etc.
    """
    filename: str = Field(description="path of the file")
    quest: str = Field(description="the initial quest to the thought")


class ToolThought(Thought, BaseModel):
    name: str = Field(description="name of the thought")
    description: str = Field(
        description="describe the usage or specialty of the thought",
    )
    prompt: str = Field(description="system prompt for the thought")
    libraries: List[str] = Field()
    tools: List[str] = Field()


class DAGThought(Thought, BaseModel, ABC):
    pass


class FlowThought(Thought, BaseModel, ABC):
    """
    Flow thought is a planner which defines a flowchart like plan, using multiple thoughts as node of it.
    Each node play a part of the plan, and determine what should go next.
    """
    name: str = Field(description="name of the plan")
    description: str = Field(description="description of the plan.")
    instruction: str = Field(description="instruction/purpose/knowledge for the whole plan, each node shares it.")
    nodes: List[FlowThoughtNode] = Field(
        description="use multiple nodes to create a flowchart like graph to resolve issues.",
    )
    start: str = Field(description="start node name of the plan")
    on_finish: str = Field(description="prompting the thought how to response when the plan is done")
    on_error: str = Field(description="prompting the thought how to response when the plan fails")


class Agent(BaseModel):
    name: str
    desc: str
    prompt: str
    root_thought: Thought


class FakeToolThought(ToolThought):
    def get_description(self) -> str:
        pass

    def new_task_id(self, g: Ghost) -> str:
        pass

    def to_entity_meta(self) -> EntityMeta:
        pass

    def identifier(self) -> Identifier:
        pass

    @classmethod
    def entity_type(cls) -> str:
        pass

    @classmethod
    def new_entity(cls, con: Container, meta: EntityMeta) -> Optional["EntityClass"]:
        pass


class FakeFlowThought(FlowThought):
    def get_description(self) -> str:
        pass

    def new_task_id(self, g: Ghost) -> str:
        pass

    def to_entity_meta(self) -> EntityMeta:
        pass

    def identifier(self) -> Identifier:
        pass

    @classmethod
    def entity_type(cls) -> str:
        pass

    @classmethod
    def new_entity(cls, con: Container, meta: EntityMeta) -> Optional["EntityClass"]:
        pass


class FakeFileThought(FileThought):

    @classmethod
    def entity_type(cls) -> str:
        pass

    @classmethod
    def new_entity(cls, con: Container, meta: EntityMeta) -> Optional["EntityClass"]:
        pass

    def get_description(self) -> str:
        pass

    def new_task_id(self, g: Ghost) -> str:
        pass

    def to_entity_meta(self) -> EntityMeta:
        pass

    def identifier(self) -> Identifier:
        pass


EXPORTS = Exporter().source_code(FakeFileThought, FileThought, 'FileThought')
