from typing import List
from abc import ABC
from pydantic import BaseModel, Field


class Shell(BaseModel):
    """
    shell that connected to the current session
    """
    name: str = Field(description="name of the shell")
    id: str = Field(description="id of the shell")


class Env(ABC, BaseModel):
    """

    """


class Context(ABC):
    """
    """
    thread = None
    self = None

    # env information
    envs: List[Env]

    # shells of the current ghost
    shells: List[Shell]

    agents: List

    users: List

    objects: List
