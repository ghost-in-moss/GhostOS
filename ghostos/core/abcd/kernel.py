from __future__ import annotations
from typing import Protocol, Optional, Iterable, List, Dict, Tuple, Callable, TypeVar, Union, Literal
from abc import ABC, abstractmethod

import urllib3.util

from ghostos.container import Container, Provider, Any
from ghostos.common import IdentifierProtocol
from ghostos.contracts.logger import LoggerItf
from ghostos.core.moss import MossRuntime
from ghostos.core.messages import Message, DefaultMessageTypes
from .ghostos_data_objects import *


class Frame(Protocol):
    id: str
    parent_id: Union[str, None]
    args: dict
    state: dict
    status: Literal["created", "running", "finished", ""]
    result: Union[dict, None]
    callback_id: str
    callback_data: dict


class Function(Protocol):
    @abstractmethod
    def on_event(self, runtime: Runtime, frame: Frame, event: Event) -> Operator:
        pass


class Future(Protocol):
    id: str
    name: str
    arguments: dict
    state: dict
    returns: Any


class Operator(Protocol):

    @abstractmethod
    def run(self, runtime: Runtime) -> Optional[Operator]:
        pass


class Thread(Protocol):
    pass


class Runtime(Protocol):
    container: Container
    frame: StackFrame
    event: Event
    thread: Thread
    logger: LoggerItf

    @abstractmethod
    def send(self, messages: Iterable[Message], actions: List[Action]) -> Operator:
        pass

    @abstractmethod
    def wait(self) -> Operator:
        pass

    @abstractmethod
    def submit(self, func: Callable, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def destroy(self):
        pass

    @abstractmethod
    def save(self):
        pass


class Kernel(Protocol):

    def get_stack(self, session_id: str) -> Run:
        pass

    def create_runtime(self, session_id: str) -> Runtime:
        pass

    def run(self, runtime: Runtime, max_times: int) -> None:
        op = runtime.ghost.on_event(runtime, runtime.event)
        count = 0
        while op is not None:
            if count > max_times:
                raise RuntimeError(f"Operator exceeds max times {max_times}")
            next_op = op.run(runtime)
            count += 1
            if next_op is not None:
                op = next_op
