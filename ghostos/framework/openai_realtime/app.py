from typing import Optional, Tuple, List, Iterable
from .configs import OpenAIRealtimeAppConf
from .client import AppClient
from .state_of_client import SynchronizingState, StateOfClient, AppState
from .output import OutputBuffer, DefaultOutputBuffer
from collections import deque
from queue import Empty
from ghostos.abcd import Conversation
from ghostos.core.messages import ReceiverBuffer, Message
from ghostos.abcd.realtime import RealtimeApp, Listener, Speaker
from threading import Thread
import time

__all__ = ['RealtimeAppImpl']


class RealtimeAppImpl(RealtimeApp):

    def __init__(
            self,
            conf: OpenAIRealtimeAppConf,
            conversation: Conversation,
            listener: Listener,
            speaker: Speaker,
    ):
        self._conversation = conversation
        self._config = conf
        self._listener = listener
        self._speaker = speaker
        self._started: bool = False
        self._closed: bool = False
        self._client: Optional[AppClient] = None
        self._state: Optional[StateOfClient] = None
        self._output: OutputBuffer = self._create_output_buffer()
        self._operators: deque = deque()
        self._threads: List[Thread] = []

    def _create_output_buffer(self) -> OutputBuffer:
        return DefaultOutputBuffer(self.is_closed, logger=self._conversation.logger)

    def start(self):
        if self.is_closed():
            # todo
            return
        if self._started:
            return
        self._started = True
        if self._client is None:
            self._client = AppClient(self._config, self._conversation)
        if self._state is None:
            self._state = SynchronizingState(self._client)
            self._state.on_init()
        self._threads.append(Thread(target=self._main_state_thread))
        self._threads.append(Thread(target=self._speaking_thread))
        self._threads.append(Thread(target=self._listening_thread))
        for t in self._threads:
            t.start()

    def _main_state_thread(self):
        while not self.is_closed():
            state = self._state
            if state is None:
                state = SynchronizingState(self._client)
                state.on_init()
                continue
            state: StateOfClient = state

            # run operators
            if len(self._operators) > 0:
                op = self._operators.popleft()
                next_state = state.operate(op)
            else:
                # tick frame
                next_state = state.tick_frame()

            # init next state
            if next_state is not None:
                self._operators.clear()
                next_state.on_init()
                self._state = next_state
                state.destroy()
                continue

            if state.recv_server_event():
                self._client.logger.info("handle server event")
                continue
            elif event := self._client.conversation.pop_event():
                self._client.handle_ghostos_event(event)
                continue

            time.sleep(0.2)

    def _speaking_thread(self):
        while not self.is_closed():
            response_id = self._output.get_response_id()
            if response_id is None:
                time.sleep(0.5)
                continue
            self._run_speaking_loop(response_id)

    def _run_speaking_loop(self, response_id: str):
        with self._speaker:
            while not self.is_closed():
                output_buffer = self._output
                queue = output_buffer.speaking_queue(response_id)
                if queue is None:
                    break
                try:
                    data = queue.get(block=True, timeout=1)
                    if data is None:
                        break
                    self._client.audio_buffer_append(data)
                except Empty:
                    continue

    def _listening_thread(self):
        while not self.is_closed():
            client = self._client
            if not client.is_listening():
                time.sleep(0.5)
                continue
            session_id = client.get_session_id()
            self._run_listening_loop(session_id)

    def _run_listening_loop(self, session_id: str):
        with self._listener:
            while not self.is_closed():
                client = self._client
                if not client.is_server_responding() or session_id != client.get_session_id():
                    break
                data = self._listener.hearing()
                if data is not None:
                    client.audio_buffer_append(data)
                else:
                    time.sleep(0.1)

    def close(self):
        if self._closed:
            return
        self._closed = True
        for t in self._threads:
            t.join()
        self._client.ctx.update_local_conversation()
        self._client.close()

    def is_closed(self) -> bool:
        return self._closed or self._conversation.is_closed()

    def messages(self) -> Iterable[Message]:
        return self._output.get_outputted_messages()

    def set_mode(self, *, listening: bool):
        self._client.ctx.listening = listening

    def state(self) -> Tuple[str, List[str]]:
        if self.is_closed():
            return AppState.closed, []
        elif self._state is None:
            return AppState.created, []

        state_name = self._state.state_name()
        operators = self._state.operators()
        return state_name, operators

    def operate(self, operator: str) -> bool:
        if self.is_closed():
            return False
        if self._state is None:
            return False
        if self._state.allow(operator):
            self._operators.append(operator)
            return True
        return False

    def fail(self, error: Exception) -> bool:
        self._client.logger.exception(error)
        self.close()
        return True

    def output(self) -> Optional[ReceiverBuffer]:
        return self._output.output_item()
