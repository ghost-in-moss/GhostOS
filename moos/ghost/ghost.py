from typing import List
from abc import ABC
from pydantic import BaseModel


class Ghost(ABC):
    """

    """


class Agent(ABC):
    """

    """


class Mind(ABC):
    """

    """


class Memory(ABC):
    """

    """


class Tools(ABC):
    """

    """


class Shell(ABC):
    """

    """


class Env(ABC, BaseModel):
    """

    """


class Context(ABC):
    """
    ghost context
    """

    # env information
    envs: List[Env]

    # shells of the current ghost
    shells: List[Shell]
