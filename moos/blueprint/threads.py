from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict, List, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from enum import Enum

from .messages import Message


class Thread(BaseModel):
    id: str = Field(description="Thread ID")


class Variable(BaseModel):
    name: str = Field(description="variable name")
    desc: str = Field(description="variable description")
    wrapper: Optional[str] = Field(default=None, description="variable wrapper")


class ThreadMsg(BaseModel):
    """
    message in the thread
    """
    id: str = Field(description="thread message id")
    reply_to: str = Field(default="", description="thread message id")
    trace: str = Field(default="", description="thread message id in which this message is created")
    thread_id: str = Field(description="thread id in which this message is created")

    message: Message = Field(default_factory=Message, description="thread message body")

    runtime_imports: Optional[List[str]] = Field(default=None, description="runtime imports")
    runtime_codes: Optional[str] = Field(default=None, description="thread message body")
    runtime_vars: Optional[List[Variable]] = Field(default=None, description="")
    runtime_values: Optional[Dict[str, Any]] = Field(default=None, description="thread message body")


class Threads(ABC):
    """
    threads api
    """

    @abstractmethod
    def get_thread(self, thread_id: str) -> Thread:
        pass

    @abstractmethod
    def save_thread(self, thread: Thread) -> None:
        pass

    @abstractmethod
    def append_thread(self, thread: Thread, *messages: "Message") -> None:
        pass
