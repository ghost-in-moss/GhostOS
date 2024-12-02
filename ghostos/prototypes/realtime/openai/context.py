from __future__ import annotations
from .event_from_server import *
from .ws import OpenAIWSConnection
from .configs import SessionObject, OpenAIRealtimeConf
from ghostos.core.messages import Message
from ghostos.abcd import Conversation, GoThreadInfo
from queue import Queue


class Context(Protocol):
    conf: OpenAIRealtimeConf
    session_obj: SessionObject
    connection: OpenAIWSConnection
    conversation: Conversation
    thread: GoThreadInfo
    messages: List[Message]

    receiving_server_event: bool = False
    is_outputting: bool = False

    listening: bool = False
    """if the client side shall listen """

    # when realtime server is speaking, the audio bytes shall send through the speaking_queue
    speaking: bool = False
    speaking_queue: Optional[Queue] = None

    outputting_id: Optional[str] = None
    outputting_chunks: Dict[str, List[Message]]
    outputting_completes: Dict[str, List[Message]]
