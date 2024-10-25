from __future__ import annotations
from typing import Self, Literal, List, Optional, Union, Dict
from enum import Enum
from ghostos.prototypes.realtime.abcd import SessionProtocol, Function, RealtimeAgent, S, ConversationProtocol, Shell, \
    Runtime
from ghostos.helpers import uuid
from pydantic import BaseModel, Field
from .protocols import SessionObj, SessionObjBase


class Session(BaseModel, SessionProtocol):
    instructions: str = Field(description="Instructions")
    shell_funcs: Dict[str, List[Function]] = Field(default_factory=dict)
    temperature: float = Field(default=0.8)
    max_response_output_tokens: Union[int, Literal['inf']] = Field(default='inf')

    def to_session_obj(self) -> SessionObj:
        raise NotImplementedError("todo")


class Conf(BaseModel):
    """
    conf of the openai realtime agent
    """
    name: str = Field()
    instructions: str = Field()
    session: SessionObjBase


class Agent(RealtimeAgent[Session]):

    def run_util_stop(
            self,
            session: Session,
            conversation: Optional[ConversationProtocol] = None,
            *shells: Shell,
    ) -> Runtime:
        pass
