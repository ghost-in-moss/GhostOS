from __future__ import annotations
from typing import Protocol, Optional, Iterable, List, Dict


class Task(Protocol):
    class Args(Protocol):
        pass

    class Result(Protocol):
        pass


class Function(Protocol):
    pass


class Message(Protocol):
    pass


class Prompt(Protocol[Function]):
    id: str
    system: List[Message]
    history: List[Message]
    inputs: Iterable[Message]
    thinks: Iterable[Message]
    instructions: Iterable[Message]
    tools: Dict[str, Function]


class Event(Protocol):
    pass


class Turn(Protocol):
    id: str
    event: Optional[Event]
    thinks: List[Message]
    actions: List[Message]


class Conversation(Protocol[Function]):
    id: str
    turns: List[Turn]
