from __future__ import annotations
from typing import Protocol, Optional, Iterable, List, Dict
from abc import ABC, abstractmethod
from ghostos.container import Container, Provider
from ghostos.common import IdentifierProtocol
from ghostos.contracts.logger import LoggerItf
from .transport import Message


class Agent(IdentifierProtocol, Protocol):

    @abstractmethod
    def meta_instruction(self) -> str:
        pass
