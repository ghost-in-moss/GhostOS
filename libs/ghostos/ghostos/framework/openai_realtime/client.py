import base64
from typing import Dict, Optional, List
from ghostos.abcd import Conversation
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.assets import AudioAssets
from ghostos.core.messages import Message, MessageType
from ghostos.core.runtime import Turn, Event as GhostOSEvent, EventTypes as GhostOSEventTypes
from io import BytesIO
from ghostos.framework.openai_realtime.configs import OpenAIRealtimeAppConf
from ghostos.framework.openai_realtime.ws import OpenAIWSConnection
from ghostos.framework.openai_realtime.event_data_objects import MessageItem, SessionObject, Tool
from ghostos.framework.openai_realtime.event_from_server import ServerSessionCreated
from ghostos.framework.openai_realtime.event_from_client import (
    SessionUpdate,
    ClientEvent,
    ConversationItemCreate,
    ResponseCancel,
    ResponseCreate,
    InputAudioBufferCommit,
    InputAudioBufferClear,
    InputAudioBufferAppend,
)
from ghostos.framework.openai_realtime.state_of_server import ServerContext, SessionState
from ghostos.framework.openai_realtime.state_of_client import Client
from ghostos.framework.openai_realtime.output import OutputBuffer
from threading import Lock
import wave

RATE = 24000


class Context(ServerContext):

    def __init__(
            self,
            *,
            conversation: Conversation,
            connection: OpenAIWSConnection,
            listening: bool,
            output: OutputBuffer,
            logger: Optional[LoggerItf] = None,

    ):
        self.conversation: Conversation = conversation
        self.connection = connection
        self.thread = conversation.get_thread(truncated=True)
        self.history_messages: Dict[str, Message] = {}
        self.history_message_order: List[str] = []
        self._reset_history_messages()

        if logger is None:
            logger = conversation.logger
        self.logger = logger

        self.buffer_message_ids: List[str] = []
        self.buffer_messages: Dict[str, Message] = {}
        self.output_buffer: OutputBuffer = output
        self.listening: bool = listening
        self.response_id: Optional[str] = None
        self.response_audio_buffer: Dict[str, BytesIO] = {}

        self.client_audio_buffer: BytesIO = BytesIO()
        self.client_audio_buffer_locker: Lock = Lock()
        self.update_history_locker: Lock = Lock()
        self._destroyed = False

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        self.connection = None
        self.conversation = None
        self._reset_buffer_messages()
        self._reset_history_messages()

    def get_server_response_id(self) -> Optional[str]:
        return self.response_id

    def _add_history_message(self, message: Message):
        if message.msg_id not in self.history_messages:
            self.history_message_order.append(message.msg_id)
            self.history_messages[message.msg_id] = message

    def _reset_history_messages(self):
        self.history_messages: Dict[str, Message] = {}
        self.history_message_order: List[str] = []
        for message in self.thread.get_messages(True):
            self.history_messages[message.msg_id] = message
            self.history_message_order.append(message.msg_id)

    def _reset_buffer_messages(self):
        self.buffer_message_ids = []
        self.buffer_messages: Dict[str, Message] = {}

    def update_local_conversation(self) -> None:
        buffered = []
        function_call = False
        for msg_id in self.buffer_message_ids:
            if msg_id in self.history_messages:
                # already updated.
                continue
            message = self.buffer_messages[msg_id]
            if not message.is_complete():
                continue
            buffered.append(message)
            if message.type == MessageType.FUNCTION_CALL:
                function_call = True
        self._reset_buffer_messages()
        if not buffered:
            return

        event_type = GhostOSEventTypes.ACTION_CALL if function_call else GhostOSEventTypes.INPUT
        event = event_type.new(
            task_id=self.conversation.task_id,
            messages=buffered
        )
        if not function_call:
            self.thread.new_turn(event)
            self.conversation.update_thread(self.thread)
            self.thread = self.conversation.get_thread(True)
        else:
            receiver = self.conversation.respond_event(event, streaming=False)
            with receiver:
                for item in receiver.recv():
                    if item.is_complete():
                        self.logger.info("receive conversation message: %s, %s", item.type, item.msg_id)
                        self.add_message_to_server(item)

        self._reset_history_messages()
        # update audio buffer
        for item_id in self.response_audio_buffer:
            buffer = self.response_audio_buffer[item_id]
            buffer.seek(0)
            data = buffer.getvalue()
            buffer.close()
            self.save_audio_data(item_id, data)
        self.response_audio_buffer = {}

    def respond_message_chunk(self, response_id: str, chunk: Optional[Message]) -> bool:
        if chunk is None:
            return False
        ok = self.output_buffer.add_response_chunk(response_id, chunk)
        if not ok:
            self.logger.debug(f"Failed to add response chunk: {response_id}")
        return ok

    def respond_error_message(self, error: str) -> None:
        message = MessageType.ERROR.new(content=error)
        self.output_buffer.add_error_message(message)

    def save_audio_item(self, item: MessageItem) -> None:
        if not item.has_audio():
            return
        audio_data = item.get_audio_bytes()
        self.save_audio_data(item.id, audio_data)

    def save_audio_data(self, item_id: str, audio_data: bytes) -> None:
        if not audio_data:
            return
        buffer = BytesIO()
        with wave.open(buffer, 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            # todo: save rate by configs
            f.setframerate(24000)
            f.writeframes(audio_data)

        saving = buffer.getvalue()

        asserts = self.conversation.container().force_fetch(AudioAssets)
        fileinfo = asserts.get_fileinfo(item_id)
        if fileinfo is None:
            fileinfo = asserts.new_fileinfo(
                fileid=item_id,
                filename=f"{item_id}.wav",
            )
        asserts.save(fileinfo, saving)

    def update_history_message(self, message: Optional[Message]) -> None:
        if message is None:
            return
        if not message.is_complete():
            # only complete message is useful
            return
        if not message.content or not message.msg_id:
            return

        if message.msg_id in self.history_messages:
            # if the history message already exists, update it
            self.history_messages[message.msg_id] = message
            self.thread.update_message(message)
        else:
            # otherwise, add the message to buffer message and try to send it.
            if message.msg_id not in self.buffer_messages:
                self.buffer_message_ids.append(message.msg_id)
            self.buffer_messages[message.msg_id] = message

    def add_message_item(self, item: MessageItem, previous_item_id: Optional[str] = None) -> None:
        if item is None:
            return
        message = item.to_complete_message()
        if message is not None:
            self.update_history_message(message)
            self.output_buffer.add_message(message, previous_item_id)

    def start_server_response(self, response_id: str) -> None:
        self.response_id = response_id
        self.output_buffer.start_output(response_id)

    def is_server_responding(self) -> bool:
        return self.response_id is not None

    def end_server_response(self, response_id: str) -> bool:
        match = response_id == self.response_id
        self.response_id = None
        return self.output_buffer.end_output(response_id) and match

    def stop_listening(self) -> bool:
        if self.listening:
            self.listening = False
            self.clear_client_audio_buffer()
            return True
        return False

    def respond_audio_chunk(self, response_id: str, item_id: str, data: bytes) -> bool:
        if response_id == self.response_id:
            if item_id not in self.response_audio_buffer:
                self.response_audio_buffer[item_id] = BytesIO()
            buffer = self.response_audio_buffer[item_id]
            buffer.write(data)
            return self.output_buffer.add_audio_output(response_id, data)

    def add_message_to_server(self, message: Message, previous_item_id: Optional[str] = None) -> bool:
        item = MessageItem.from_message(message)
        if item is not None:
            ce = ConversationItemCreate(
                previous_item_id=previous_item_id,
                item=item,
            )
            self.send_client_event(ce)
            return True
        return False

    def send_client_event(self, event: ClientEvent, exclude_none=True):
        data = event.to_event_dict(exclude_none=exclude_none)
        self.logger.debug("send client event type %s", type(event))
        self.connection.send(data)

    def audio_buffer_append(self, buffer: bytes) -> None:
        with self.client_audio_buffer_locker:
            content = base64.b64encode(buffer)
            self.client_audio_buffer.write(buffer)
        ce = InputAudioBufferAppend(
            audio=content
        )
        self.send_client_event(ce)

    def clear_client_audio_buffer(self) -> None:
        with self.client_audio_buffer_locker:
            self.client_audio_buffer.close()
            self.client_audio_buffer = BytesIO()
        if self.listening:
            ce = InputAudioBufferClear()
            self.send_client_event(ce)

    def set_client_audio_buffer_start(self, cut_ms: int) -> None:
        pass
        # with self.client_audio_buffer_locker:
        #     data = self.client_audio_buffer.getvalue()
        #     cut = int((RATE / 1000) * cut_ms)
        # if cut < len(data):
        #     cut_data = data[cut:]
        #     self.client_audio_buffer = BytesIO(cut_data)

    def set_client_audio_buffer_stop(self, item_id: str, end_ms: int) -> None:
        with self.client_audio_buffer_locker:
            data = self.client_audio_buffer.getvalue()
            # cut = int((RATE / 1000) * end_ms)
            # cut_data = data[:cut]
            # if cut < len(data):
            #     left_data = data[cut:]
            #     self.client_audio_buffer = BytesIO(left_data)
            self.save_audio_data(item_id, data)
        self.client_audio_buffer.close()
        self.client_audio_buffer = BytesIO()


class AppClient(Client):

    def __init__(
            self,
            conf: OpenAIRealtimeAppConf,
            vad_mode: bool,
            output_buffer: OutputBuffer,
            conversation: Conversation,
    ):
        self._closed: bool = False
        self._vad_mode = vad_mode
        self.conf: OpenAIRealtimeAppConf = conf
        self.conversation: Conversation = conversation
        self.logger = conversation.logger
        self.connection: OpenAIWSConnection = self.connect()
        self.server_ctx: Context = Context(
            conversation=conversation,
            connection=self.connection,
            listening=self._vad_mode,
            logger=conversation.logger,
            output=output_buffer,
        )
        self.session_state: SessionState = self._create_session_state()
        self.synchronized: bool = False
        self._sync_history: Optional[List[str]] = None

    def set_vad_mode(self, vad_mode: bool) -> None:
        if vad_mode == self._vad_mode:
            return
        self._vad_mode = vad_mode
        self.update_session()

    def vad_mode(self) -> bool:
        return self._vad_mode

    def connect(self) -> OpenAIWSConnection:
        self._validate_closed()
        self._sync_history = None
        self.synchronized = False
        return OpenAIWSConnection(
            self.conf.ws_conf,
            logger=self.logger,
        )

    def _validate_closed(self):
        if self._closed:
            raise RuntimeError("App Client is closed")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.connection:
            self.connection.close()
        if self.session_state:
            self.session_state.destroy()
        if self.server_ctx:
            self.server_ctx.destroy()
        del self.connection
        del self.session_state
        del self.server_ctx

    def get_session_id(self) -> str:
        self._validate_closed()
        if self.session_state:
            return self.session_state.session_id
        return ""

    def reconnect(self) -> None:
        self._validate_closed()
        if self.connection is not None:
            connection = self.connection
            connection.close()
        if self.session_state is not None:
            self.session_state.destroy()
        self.session_state = None

        self.connection: OpenAIWSConnection = self.connect()
        self.session_state: SessionState = self._create_session_state()
        self.synchronized = False

    def audio_buffer_append(self, buffer: bytes) -> None:
        if not self.is_listening():
            # listening change is quick then sending
            return
        self.server_ctx.audio_buffer_append(buffer)

    def is_listening(self) -> bool:
        if not self.synchronized:
            return False
        if self.server_ctx.is_server_responding():
            return False
        if self.server_ctx.output_buffer.is_speaking():
            return False
        return self.server_ctx.listening

    def listen_mode(self) -> bool:
        return self.server_ctx.listening

    def _create_session_state(self) -> SessionState:
        e = self.connection.recv(timeout=self.conf.session_created_timeout, timeout_error=True)
        se = ServerSessionCreated(**e)
        return SessionState(self.server_ctx, se)

    def update_session(self):
        session_obj = self.get_session_obj()
        ce = SessionUpdate(
            session=session_obj.model_dump(),
        )
        self.logger.debug("client update session: %r", ce)
        self.server_ctx.send_client_event(ce, exclude_none=False)

    def get_sync_history(self):
        if self._sync_history is not None:
            return self._sync_history
        history = []
        for msg_id in self.server_ctx.history_message_order:
            message = self.server_ctx.history_messages[msg_id]
            if not message.content:
                continue
            history.append(message.role + ": " + message.content)
        self._sync_history = history
        return self._sync_history

    def get_session_obj(self) -> SessionObject:
        session_obj = self._get_session_obj(self._vad_mode)
        history = self.get_sync_history()
        if history:
            history_content = "\n\n---\n\n".join(history)
            session_obj.instructions += "\n\n# history messages\n\n" + history_content
        return session_obj

    def synchronize_server_session(self):
        if self.synchronized:
            return
        count = 0
        self.update_session()
        self.logger.info("Synchronizing server session done with item %d", count)
        self.synchronized = True

    def cancel_responding(self) -> bool:
        # cancel local response first.
        self.server_ctx.output_buffer.stop_output(None)
        if self.server_ctx.is_server_responding():
            ce = ResponseCancel()
            self.server_ctx.send_client_event(ce)
            self.clear_audio_input()
            return True
        return False

    def start_listening(self) -> bool:
        if not self.server_ctx.listening:
            self.server_ctx.listening = True
            self.server_ctx.output_buffer.stop_output(None)
            if self.server_ctx.is_server_responding():
                self.cancel_responding()
            return True
        return False

    def stop_listening(self) -> bool:
        return self.server_ctx.stop_listening()

    def commit_audio_input(self) -> bool:
        if self.server_ctx.listening:
            ce = InputAudioBufferCommit()
            self.server_ctx.send_client_event(ce)
            return True
        return False

    def clear_audio_input(self) -> bool:
        if self.server_ctx.listening:
            ce = InputAudioBufferClear()
            self.server_ctx.send_client_event(ce)
            return True
        return False

    def _get_session_obj(self, vad_mode: bool) -> SessionObject:
        session_obj = self.conf.get_session_obj(vad_mode)
        session_obj.instructions = self.conversation.get_system_instruction()
        tools = []
        for fn in self.conversation.get_functions():
            tool = Tool(**fn.to_dict())
            tools.append(tool)
        session_obj.tools = tools
        return session_obj

    def create_response(self) -> bool:
        session_obj = self.get_session_obj()
        ce = ResponseCreate(
            response=session_obj.model_dump(),
        )
        self.server_ctx.send_client_event(ce)
        return True

    def is_server_responding(self) -> bool:
        return self.server_ctx.is_server_responding()

    def is_speaking(self) -> bool:
        return self.server_ctx.output_buffer.is_speaking()

    def receive_server_event(self) -> bool:
        data = self.connection.recv(timeout=0.1)
        if data:
            self.logger.debug("got received server event")
            self.session_state.recv(data)
            return True
        return False

    def handle_ghostos_event(self, event: GhostOSEvent):
        # send message to server, let the realtime server handle the new message items.
        for msg in Turn.iter_event_message(event):
            self.server_ctx.add_message_to_server(msg)

    def respond_error_message(self, error: str) -> None:
        self.server_ctx.respond_error_message(error)
