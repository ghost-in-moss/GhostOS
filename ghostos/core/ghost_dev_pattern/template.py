from .concepts import Func, Context, State, OP
from typing import List, Union
from pydantic import BaseModel, Field
from ghostos.core.moss import Moss


class Chat(Func):
    class Args(BaseModel):
        instruction: str

    class Returns(BaseModel):
        summary: str


class ChatState(State):
    who_is_talking: str
    notes: List[str]


class ChatMoss(Moss):
    pass


def main(ctx: Context[Chat, ChatState, ChatMoss]) -> OP:
    """
    instructions
    """
    pass
