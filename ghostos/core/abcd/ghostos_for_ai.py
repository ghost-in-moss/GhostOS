from typing import Protocol, TypeVar, Optional
from abc import ABC, abstractmethod
from .ghostos_data_objects import Task

T = TypeVar("T", bound=Task)


class State(Protocol[T]):

    @abstractmethod
    def on_args(self, args: T.Args):
        pass

    @abstractmethod
    def result(self) -> Optional[T.Result]:
        pass


S = TypeVar("S", bound=State)


class Moss(Protocol):
    state: State


def think(moss: Moss) -> None:
    """
    :param moss:
    """
    pass

def action(moss: Moss) -> None:
    pass
