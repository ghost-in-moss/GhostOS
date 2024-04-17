from __future__ import annotations
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum


class History(BaseModel):
    """
    reaction(chat or other) history
    """
    scope: Scope = Field(description="message history scope")
    messages: List[Message] = Field(description="message history")


class Message(BaseModel):
    """
    message
    """
    header: Header = Field(description="message header")
    model: ModelInfo = Field(description="model info")
    body: Optional[Body] = Field(default=None, description="message body")
    codes: Optional[str] = Field(default=None, description="python runtime codes after the message")


class Scope(BaseModel):
    # runtime scope fields
    session_id: str = Field(description="id of the session")
    process_id: str = Field(description="id of the process in the session")
    thread_id: str = Field(description="id of the thread in the session process")
    task_id: str = Field(description="id of the task in which the message was sent")


class Role(Enum):
    ASSISTANT = "assistant"
    FUNCTION = "function"
    USER = "user"
    SYSTEM = "system"

    @classmethod
    def all(cls) -> List[str]:
        return [cls.ASSISTANT.value, cls.FUNCTION.value, cls.USER.value, cls.SYSTEM.value]


class Header(BaseModel):
    """
    Message Header
    """
    id: str = Field(description="message id")
    ref: str = Field(default="", description="referred message id")
    role: str = Field(description="role of the message sender", enum=Role.all())
    name: str = Field(default="", description="name of the message sender")

    # ghost scope fields
    ghost_id: str = Field(default="", description="id of the ghost who sent the message")
    thought_id: str = Field(default="", description="id of the thought of the ghost who sent the message")
    user_id: str = Field(default="", description="id of the user who sent the message")


class Kind(Enum):
    TEXT = "text"  # text only
    PYTHON = "py"  # ghost want to execute python
    PYTHON_DEF = "def"  # ghost want to define python codes
    FUNCTION_CALL = "fc"  # ghost want to execute a local function


class Body(BaseModel):
    """
    message content
    """
    kind: str = Field(description="kind of the message")
    content: str = Field(description="message body")
    payload: Optional[Dict] = Field(default=None, description="message payload")


class ModelInfo(BaseModel):
    """
    model info from which generate the message
    """
    name: str = Field(default="", description="name of the model")
    server: str = Field(default="", description="name of the server")
    tokens: int = Field(default=0, description="count of tokens")
