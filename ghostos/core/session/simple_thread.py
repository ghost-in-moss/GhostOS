from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ghostos.core.messages import Message
from ghostos.core.session.threads import MsgThread, Turn

DESCRIPTION = """
Simple Thread is a simple mode for MsgThread, useful to show thread important information when debugging.
"""


class SimpleMessage(BaseModel):
    """
    Message adapter
    """

    name: Optional[str] = Field(None)
    role: str = Field(description="role of the message")
    content: str = Field(description="content of the message")
    memory: Optional[str] = Field(default=None, description="memory of the message")

    @classmethod
    def from_message(cls, msg: Message) -> "SimpleMessage":
        return cls(
            name=msg.name,
            role=msg.role,
            content=msg.content,
            memory=msg.memory,
        )


class SimpleTurn(BaseModel):
    idx: int = Field(default=-1)
    extra: Dict[str, Any] = Field(default_factory=dict)
    messages: List[SimpleMessage] = Field(default_factory=list)

    @classmethod
    def from_turn(cls, turn: Turn, idx: int = 0) -> Optional["SimpleTurn"]:
        if turn.is_empty():
            return None
        return cls(
            idx=idx,
            messages=[SimpleMessage.from_message(msg) for msg in turn.messages()],
            extra=turn.extra,
        )


class SimpleMsgThread(BaseModel):
    thread_id: str = Field(description="thread id that useful to save & read thread")
    extra: Dict[str, Any] = Field(default_factory=dict)
    system_prompt: str = Field(defualt="", description="system prompt")
    turns: List[SimpleTurn] = Field(default_factory=list)

    @classmethod
    def from_thread(cls, thread: MsgThread) -> "SimpleMsgThread":
        turns = []
        idx = 0
        for turn in thread.turns():
            st = SimpleTurn.from_turn(turn, idx)
            if st is not None:
                turns.append(st)
                idx += 1
        return cls(
            thread_id=thread.id,
            system_prompt=thread.system_prompt,
            turns=turns,
            extra=thread.extra,
        )
