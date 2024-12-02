from __future__ import annotations
from abc import ABC, abstractmethod
from queue import Queue
from collections import deque
import time
from typing import List, Optional, Dict, Iterable, Tuple, Callable, Union
from threading import Thread
from ghostos.abcd import Conversation
from ghostos.core.messages import ReceiverBuffer
from ghostos.prototypes.realtime.abcd import (
    RealtimeApp,
    Listener, Speaker,
    RealtimeOperator,
)
from collections import deque
from ghostos.container import Container
from ghostos.core.messages import (
    Message,
)
from ghostos.contracts.logger import LoggerItf, get_logger
from ghostos.contracts.pool import DefaultPool
# from concurrent.futures import ThreadPoolExecutor
# from queue import Queue
# from .protocols import StateName, ServerEventType
from .configs import OpenAIRealtimeConf
from .ws import OpenAIWSConnection, OpenAIWebsocketsConf

from abc import ABC, abstractmethod

from .app import RealtimeApp
from .event_from_server import *
from .configs import OpenAIRealtimeConf
from ghostos.prototypes.realtime.abcd import RealtimeOperator, State


class OpenAIRealtimeContext:

    def __init__(
            self,
            conversation: Conversation,
            conf: OpenAIRealtimeConf,
            logger: LoggerItf,
    ):
        self.conversation = conversation
        self.logger = logger
        self.error: Optional[Exception] = None
        self.conf: OpenAIRealtimeConf = conf
        self.listening: bool = False
        self.speaking_queue: Queue = Queue()
        self.speaking_id: Optional[str] = None
        self.buffer: List[Message] = []
        self.outputting_completed: Dict[int, Message] = {}
        self.outputting_chunks: Dict[int, List[Message]] = {}
        self.outputting_id: Optional[int] = None
        self.connection: Optional[OpenAIWSConnection] = None
        self.closed: bool = False

    def is_closed(self) -> bool:
        return self.closed or self.conversation.closed()

    def stop_speaking(self):
        self.speaking_id = None
        self.speaking_queue.put(None)
        self.speaking_queue = Queue()

    def start_speaking(self, speaking_id: str):
        self.speaking_queue.put(None)
        self.speaking_id = speaking_id
        self.speaking_queue = Queue()

    def messages(self) -> Iterable[Message]:
        pass

    def push_message(self, message: Message):
        pass

    def add_message_to_server(self, message: Message):
        pass

    def default_handle_server_event(self, event: dict):
        if ServerEventType.error.match(event):
            pass
        elif ServerEventType.session_created.match(event):
            pass
        elif ServerEventType.session_updated.match(event):
            pass
        elif ServerEventType.conversation_created.match(event):
            pass
        elif ServerEventType.conversation_item_created.match(event):
            pass
        elif ServerEventType.conversation_item_deleted.match(event):
            pass
        elif ServerEventType.audio_transcript_created.match(event):
            pass
        elif ServerEventType.audio_transcript_failed.match(event):
            pass
        elif ServerEventType.response_output_item_done.match(event):
            pass


class Connecting(State):

    def __init__(self, ctx: OpenAIRealtimeContext):
        self.ctx = ctx

    def name(self) -> str:
        return "Connecting"

    def is_outputting(self) -> bool:
        return False

    def run_frame(self) -> Optional[State]:
        ws_conf = self.ctx.conf.ws_conf
        if self.ctx.connection:
            self.ctx.connection.close()
        self.ctx.connection = OpenAIWSConnection(ws_conf, logger=self.ctx.logger)
        return Connected(self.ctx)

    def allow(self, op: RealtimeOperator) -> Tuple[bool, Optional[str]]:
        return False, "not implemented"

    def handle(self, op: RealtimeOperator) -> Optional[State]:
        event = self.ctx.connection.recv()
        if event is None:
            return None

        return self

    def destroy(self):
        del self.ctx


class Connected(State):

    def __init__(self, ctx: OpenAIRealtimeContext):
        self.ctx = ctx

    def name(self) -> str:
        return "Connected"

    def allow(self, op: RealtimeOperator) -> Tuple[bool, Optional[str]]:
        pass

    def is_outputting(self) -> bool:
        pass

    def handle(self, op: RealtimeOperator) -> Optional[State]:
        pass

    def run_frame(self) -> Optional[State]:
        event = self.ctx.connection.recv()
        if event is None:
            return None
        if ServerEventType.session_created.match(event):
            return SyncConversation(self.ctx)

    def destroy(self):
        pass


class SyncConversation(State):
    def __init__(self, ctx: OpenAIRealtimeContext):
        self.ctx = ctx

    def name(self) -> str:
        pass

    def allow(self, op: RealtimeOperator) -> Tuple[bool, Optional[str]]:
        pass

    def is_outputting(self) -> bool:
        pass

    def handle(self, op: RealtimeOperator) -> Optional[State]:
        pass

    def run_frame(self) -> Optional[State]:
        for msg in self.ctx.messages():
            self.ctx.add_message_to_server(msg)

    def destroy(self):
        pass


class WaitingServer(State):
    def __init__(self, ctx: OpenAIRealtimeContext):
        self.ctx = ctx

    def name(self) -> str:
        pass

    def allow(self, op: RealtimeOperator) -> Tuple[bool, Optional[str]]:
        pass

    def is_outputting(self) -> bool:
        pass

    def handle(self, op: RealtimeOperator) -> Optional[State]:
        pass

    def run_frame(self) -> Optional[State]:
        event = self.ctx.connection.recv()
        if event is None:
            return None
        if ServerEventType.conversation_created.match(event):
            # todo
            return None

    def destroy(self):
        pass


class Listening(State):
    def __init__(self, ctx: OpenAIRealtimeContext):
        self.ctx = ctx

    def is_outputting(self) -> bool:
        return True


class Responding(State):
    def __init__(self, ctx: OpenAIRealtimeContext):
        self.ctx = ctx

    def is_outputting(self) -> bool:
        return True
