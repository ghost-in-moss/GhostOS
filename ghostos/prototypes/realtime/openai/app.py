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
    RealtimeOP,
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
from .context import Context
from .state_of_client import StateOfClient
from .state_of_server import StateOfServer
from .ws import OpenAIWSConnection


# from .broadcast import SimpleBroadcaster, Broadcaster


class OpenAIRealtimeApp(RealtimeApp):

    def __init__(
            self,
            conf: OpenAIRealtimeConf,
            conversation: Conversation,
            listener: Listener,
            speaker: Speaker,
            proxy: Optional[Callable] = None,
    ):
        self._conf = conf
        self._state: StateOfClient = StateOfClient()
        self._conversation = conversation
        self._proxy = proxy
        self._logger = conversation.logger
        self._pool = DefaultPool(10)
        self._ctx: Context = ""
        self._server_state: StateOfServer = StateOfServer()
        self._client_state: StateOfClient = StateOfClient()
        self._operators: deque[RealtimeOP] = deque()
        self._listener: Listener = listener
        self._speaker: Speaker = speaker
        # status.
        self._started = False

    def start(self):
        if self._started:
            return
        if self._ctx.is_closed():
            raise RuntimeError("App is already closed")
        self._started = True
        self._pool.submit(self._listening_thread)
        self._pool.submit(self._speaking_thread)
        self._pool.submit(self._main_state_loop)

    def close(self):
        if self._ctx.is_closed() or not self._started:
            return
        self._ctx.closed = True
        self._pool.shutdown()
        # todo: 1. update conversation. 2. destroy dependencies.

    def is_closed(self) -> bool:
        return self._ctx.is_closed()

    def send_message(self, messages: List[Message]):
        raise NotImplementedError("Not implemented yet")

    def fail(self, error: Exception) -> bool:
        self._logger.exception(error)
        return False

    def get_state_desc(self) -> Tuple[str, bool]:
        return self._state.name(), self._state.is_outputting()

    def operate(self, op: RealtimeOP) -> Tuple[bool, Optional[str]]:
        ok, error = self._state.allow(op)
        if ok:
            self._operators.append(op)
        return ok, error

    def output(self) -> Optional[ReceiverBuffer]:
        iterator = self._output_messages()
        if iterator is None:
            return None
        return ReceiverBuffer.new(iterator)

    def messages(self) -> Iterable[Message]:
        # clear unsync messages.
        self._ctx.sync_ghostos_conversation()
        return self._ctx.thread.get_messages(truncated=True)

    def _output_messages(self) -> Optional[Iterable[Message]]:
        response_id = self._ctx.response_id
        if response_id is None:
            return None
        msg_id = None
        while response_id == self._ctx.response_id and not self.is_closed():
            if self._ctx.response_queue is None:
                return None

            if msg_id and msg_id in self._ctx.buffer_messages:
                break
            self._ctx.

    @staticmethod
    def _destroy_state(state: State) -> None:
        state._destroy()

    def _main_state_loop(self):
        while not self._ctx.is_closed():
            state = self._state
            while len(self._operators) > 0:
                op = self._operators.popleft()
                next_state = state.handle(op)
                if next_state is not None:
                    self._pool.submit(state._destroy)
                    state = next_state
                    # clear all
                    self._operators.clear()
                    continue

            next_state = state.run_frame()
            if next_state is not None:
                self._pool.submit(state._destroy)
                self._state = next_state

    def _listening_thread(self):
        while not self._closed:
            if not self._ctx.listening:
                time.sleep(0.5)
                continue
            self._try_listening()

    def _speaking_thread(self):
        while not self._closed:
            speaking_id = self._ctx.speaking_id
            if speaking_id is None:
                time.sleep(0.5)
                continue
            self._try_speaking(speaking_id, self._ctx.speaking_queue)

    def _try_speaking(self, speaking_id: str, queue: Queue):
        with self._speaker:
            while self._ctx.speaking_id and speaking_id == self._ctx.speaking_id:
                data = queue.get(block=True)
                if data is None:
                    break
                self._speaker.speak(data)

    def _try_listening(self):
        if not self._ctx.listening:
            return
        with self._listener:
            while self._ctx.listening:
                data = self._listener.hearing()
                if data is None:
                    return
                self._send_audio_buffer(data)
            buffer = self._listener.flush()

    def _send_audio_buffer(self, data: bytes) -> None:
        pass

    # def start(self) -> None:
    #     if self._started:
    #         raise RuntimeError("agent already started")
    #
    #     _funcs: Dict[str, List[Function]] = {}

    # def _main(self):
    #     # bind shells.
    #     _ctx = StateCtx(
    #         conf=self._conf,
    #         container=self._container,
    #         conversation=self._conversation,
    #         broadcaster=_broadcast,
    #         session=None,
    #         connection=None,
    #         connect_sock=self._proxy,
    #         logger=self._logger,
    #     )
    #     self._state = ConnectingState(_ctx)
    #
    #     while not self._closed:
    #         state = self._state
    #         new_state = state.tick()
    #         if new_state is None:
    #             time.sleep(0.05)
    #         else:
    #             # destroy
    #             self._pool.submit(state.join)
    #             # renew the state
    #             self._state = new_state
    #             if new_state.state_name == StateName.stopped:
    #                 # stop the world
    #                 break
    #     # recycle
    #     _broadcast.close()
    #     if self._state is not None:
    #         self._state.join()
    #
    # def close(self) -> None:
    #     if self._closed:
    #         return
    #     self._closed = True
    #     self._pool.shutdown()
    #
    # def fail(self, error: Exception) -> bool:
    #     self._logger.exception(error)
    #     self.close()
    #     return False
    #
    # def output(self) -> Optional[ReceiverBuffer]:
    #     pass

# class ConversationShell(Shell):
#     """
#     non-block conversation item updater
#     """
#
#     def __init__(self, conversation: Conversation):
#         self._conversation = conversation
#         self._recv_queue = Queue()
#         self._closed = False
#         self._main_thread = Thread(target=self._main)
#
#     def name(self) -> str:
#         return "__conversation__"
#
#     def functions(self) -> List[Function]:
#         return []
#
#     def subscribing(self) -> List[str]:
#         return ServerEventType.conversation_item_events()
#
#     def on_sync(self, ghost: Ghost) -> ChanIn[Union[dict, None]]:
#         self._main_thread.start()
#         return self._recv_queue
#
#     def _main(self):
#         while not self._closed:
#             e = self._recv_queue.get(block=True)
#             if e is None:
#                 self._closed = True
#                 break
#             self._add_conversation(e)
#
#     def _add_conversation(self, e: dict) -> None:
#         raise NotImplementedError("todo")
#
#     def destroy(self):
#         self._main_thread.join()
