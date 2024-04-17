from __future__ import annotations

from typing import Dict, Optional
from pydantic import BaseModel, Field
from .message import Kind


class Package(BaseModel):
    """
    streaming package
    """
    kind: str = Field(default="", description="package kind")
    content: str = Field(default="", description="package content")
    done: bool = Field(default=False, description="a message of the kind is done sent")
    payload: Optional[Dict] = Field(default=None, description="package payload")


class Fin(Package):
    """
    last package of the stream
    """
    kind: str = "fin"


class Text(Package):
    kind = Kind.TEXT.value

# class Tool(Package):
