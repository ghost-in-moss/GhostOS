from typing import Optional, Tuple, List, Iterable
from .configs import OpenAIRealtimeAppConf
from .client import AppClient
from .state_of_client import SynchronizingState, StateOfClient, AppState
from .output import OutputBuffer, DefaultOutputBuffer
from collections import deque
from ghostos.abcd import Conversation
from ghostos.core.messages import ReceiverBuffer, Message
from ghostos.abcd.realtime import RealtimeApp, Listener, Speaker, Operator, OperatorName
from threading import Thread
from queue import Empty
import time

__all__ = ['RealtimeAppImpl']


class RealtimeAppImpl(RealtimeApp):

    def __init__(
            self,
            *,
            conf: OpenAIRealtimeAppConf,
            vad_mode: bool,
            conversation: Conversation,
            listener: Listener,
            speaker: Speaker,
    ):
        self._conversation = conversation
        self._config = conf
        self._vad_mode = vad_mode
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
            self._client = AppClient(self._config, self._vad_mode, self._output, self._conversation)
        self._threads.append(Thread(target=self._main_state_thread))
        self._threads.append(Thread(target=self._speaking_thread))
        self._threads.append(Thread(target=self._listening_thread))
        for t in self._threads:
            t.start()

    def add_message(self, message: Message, previous_message_id: Optional[str] = None):
        self._client.add_message_to_server(message, previous_message_id)

    def _main_state_thread(self):
        try:
            while not self.is_closed():
                self._client.logger.debug("start a state frame")
                state = self._state
                if state is None:
                    self._client.logger.debug("synchronize state")
                    state = SynchronizingState(self._client)
                    state.on_init()
                    self._state = state
                    continue
                state: StateOfClient = state

                # run operators
                if len(self._operators) > 0:
                    op = self._operators.popleft()
                    self._client.logger.debug("handle operator %s", op.name)
                    next_state = state.operate(op)
                else:
                    # tick frame
                    next_state = state.tick_frame()

                # init next state
                if next_state is not None:
                    self._client.logger.debug("change state from %s to %s", state, next_state)
                    self._operators.clear()
                    next_state.on_init()
                    self._state = next_state
                    state.destroy()
                    continue

                if state.recv_server_event():
                    self._client.logger.debug("handled server event")
                    continue
                elif event := self._client.conversation.pop_event():
                    # handle ghostos event if server event is missing.
                    self._client.logger.debug("handle ghostos event")
                    self._client.handle_ghostos_event(event)
                    continue

                time.sleep(0.2)
        except Exception as e:
            self._client.logger.exception(e)
            self.close()

    def _speaking_thread(self):
        try:
            while not self.is_closed():
                response_id = self._output.get_response_id()
                if response_id is None:
                    time.sleep(0.5)
                    continue
                self._client.logger.debug("start speaking. respond id is %s", response_id)
                self._run_speaking_loop(response_id)
                self._client.logger.debug(
                    "try to stop speaking. responding is %r",
                )
                self._output.stop_speaking()
                self._client.logger.debug(
                    "stop speaking. responding is %r",
                    self._client.is_responding(),
                )
        except Exception as e:
            self._client.logger.exception(e)
            self.close()

    def _run_speaking_loop(self, response_id: str):
        output_buffer = self._output
        q = output_buffer.speaking_queue(response_id)
        if q is None:
            return

        client = self._client
        client.logger.debug("start speaking loop")

        def receive():
            try:
                item = q.get(block=True)
                return item
            except Empty:
                time.sleep(0.2)

        with self._speaker.speak(receive) as speaking:
            while not self.is_closed() and not speaking.done() and self._output.is_speaking():
                time.sleep(0.1)
        client.logger.debug("end speaking loop")

    def _listening_thread(self):
        try:
            while not self.is_closed():
                client = self._client
                if not client.is_listening():
                    time.sleep(0.1)
                    continue
                session_id = client.get_session_id()
                self._run_listening_loop(session_id)
        except Exception as e:
            self._client.logger.exception(e)
            self.close()

    def _run_listening_loop(self, session_id: str):
        client = self._client
        client.logger.debug("start listening loop")
        with self._listener.listen(client.audio_buffer_append):
            while not self.is_closed():
                if not client.is_listening():
                    break
                time.sleep(0.1)
        client.logger.debug("end listening loop")

    def close(self):
        if self._closed:
            return
        self._closed = True
        for t in self._threads:
            t.join()
        self._client.server_ctx.update_local_conversation()
        self._client.close()

    def is_closed(self) -> bool:
        return self._closed or self._conversation.is_closed()

    def history_messages(self) -> Iterable[Message]:
        return self._output.get_outputted_messages()

    def set_mode(self, *, vad_mode: bool):
        self._client.vad_mode = vad_mode
        self._client.update_session()

    def state(self) -> Tuple[str, List[Operator]]:
        if self.is_closed():
            return AppState.closed, []
        elif self._state is None:
            return AppState.created, []

        state_name = self._state.state_name()
        operators = self._state.operators()
        return state_name, operators

    def operate(self, operator: Operator) -> bool:
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
        return self._output.output_received()
