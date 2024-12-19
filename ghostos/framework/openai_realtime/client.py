import base64
from typing import Dict, Optional, List
from ghostos.abcd import Conversation
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.assets import AudioAssets
from ghostos.core.messages import Message, MessageType
from ghostos.core.runtime import Turn, Event as GhostOSEvent, EventTypes as GhostOSEventTypes
from io import BytesIO
from .configs import OpenAIRealtimeAppConf
from .ws import OpenAIWSConnection
from .event_data_objects import MessageItem, SessionObject, Content
from .event_from_server import ServerSessionCreated
from .event_from_client import (
    SessionUpdate,
    ClientEvent,
    ConversationItemCreate,
    ResponseCancel,
    ResponseCreate,
    InputAudioBufferCommit,
    InputAudioBufferClear,
    InputAudioBufferAppend,
)
from .state_of_server import ServerContext, SessionState
from .state_of_client import Client
from .output import OutputBuffer
import wave


class Context(ServerContext):

    def __init__(
            self,
            *,
            conversation: Conversation,
            listening: bool,
            output: OutputBuffer,
            logger: Optional[LoggerItf] = None,
    ):
        self.conversation: Conversation = conversation
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

    def get_server_response_id(self) -> Optional[str]:
        return self.response_id

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

        event_type = GhostOSEventTypes.ACTION_CALL if function_call else GhostOSEventTypes.NOTIFY
        event = event_type.new(
            task_id=self.conversation.task_id,
            messages=buffered
        )
        if not function_call:
            self.thread.new_turn(event)
            self.conversation.update_thread(self.thread)
            self.thread = self.conversation.get_thread(True)
            self._reset_history_messages()
        else:
            raise NotImplementedError("failed")

        # update audio buffer
        for item_id in self.response_audio_buffer:
            buffer = self.response_audio_buffer[item_id]
            buffer.seek(0)
            data = buffer.getvalue()
            buffer.close()
            self.save_audio_data(item_id, data)
        self.response_audio_buffer = {}

    def respond_message_chunk(self, response_id: str, chunk: Optional[Message]) -> bool:
        ok = self.output_buffer.add_response_chunk(response_id, chunk)
        if not ok:
            self.logger.error(f"Failed to add response chunk: {response_id}")
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

    def stop_listening(self) -> None:
        self.listening = False

    def respond_audio_chunk(self, response_id: str, item_id: str, data: bytes) -> bool:
        if response_id == self.response_id:
            if item_id not in self.response_audio_buffer:
                self.response_audio_buffer[item_id] = BytesIO()
            buffer = self.response_audio_buffer[item_id]
            buffer.write(data)
            return self.output_buffer.add_audio_output(response_id, data)


class AppClient(Client):

    def __init__(
            self,
            conf: OpenAIRealtimeAppConf,
            vad_mode: bool,
            output_buffer: OutputBuffer,
            conversation: Conversation,
    ):
        self._closed: bool = False
        self.conf: OpenAIRealtimeAppConf = conf
        self.vad_mode = vad_mode
        self.conversation: Conversation = conversation
        self.server_ctx: Context = Context(
            conversation=conversation,
            listening=self.vad_mode,
            logger=conversation.logger,
            output=output_buffer,
        )
        self.logger = conversation.logger
        self.connection: OpenAIWSConnection = self.connect()
        self.session_state: SessionState = self._create_session_state()
        self.synchronized: bool = False

    def connect(self) -> OpenAIWSConnection:
        self._validate_closed()
        return OpenAIWSConnection(
            self.conf.ws_conf,
            logger=self.server_ctx.logger,
        )

    def _validate_closed(self):
        if self._closed:
            raise RuntimeError("App Client is closed")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True

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
        content = base64.b64encode(buffer)
        ce = InputAudioBufferAppend(
            audio=content
        )
        self._send_client_event(ce)

    def is_listening(self) -> bool:
        if not self.synchronized:
            return False
        if self.server_ctx.is_server_responding():
            return False
        if self.server_ctx.output_buffer.is_speaking():
            return False
        return self.server_ctx.listening

    def _create_session_state(self) -> SessionState:
        e = self.connection.recv(timeout=self.conf.session_created_timeout, timeout_error=True)
        se = ServerSessionCreated(**e)
        return SessionState(self.server_ctx, se)

    def update_session(self):
        session_obj = self.get_session_obj(self.vad_mode)
        ce = SessionUpdate(
            session=session_obj.model_dump(exclude_none=True),
        )
        self.logger.debug("update session: %s", repr(ce))
        self._send_client_event(ce)

    def synchronize_server_session(self):
        if self.synchronized:
            return
        count = 0
        # self.update_session()
        history = []
        previous_item_id = None
        for msg_id in self.server_ctx.history_message_order:
            message = self.server_ctx.history_messages[msg_id]
            if not message.content:
                continue

            history.append(message.role + ": " + message.content)

            # ok = self.add_message_to_server(message, previous_item_id)
            # if ok:
            #     previous_item_id = message.msg_id
            # self.logger.debug("Synchronizing server session with item %s", msg_id)
            count += 1
        if history:
            history_content = "\n\n---\n\n".join(history)
            # ce = ConversationItemCreate(
            #     item=MessageItem(
            #         role="system",
            #         type="message",
            #         content=[
            #             Content(type="input_text", text=history_content),
            #         ]
            #     )
            # )
            session_obj = self.get_session_obj(self.vad_mode)
            ce = SessionUpdate(
                session=session_obj.model_dump(exclude_none=True),
            )
            ce.session.instructions += "\n\n# history messages\n\n" + history_content
            self._send_client_event(ce)
        else:
            self.update_session()

        self.logger.info("Synchronizing server session done with item %d", count)
        self.synchronized = True

    def cancel_responding(self) -> bool:
        # cancel local response first.
        self.server_ctx.output_buffer.stop_output()
        if self.server_ctx.is_server_responding():
            ce = ResponseCancel()
            self._send_client_event(ce)
            return True
        return False

    def start_listening(self) -> bool:
        if not self.server_ctx.listening:
            self.server_ctx.listening = True
            self.server_ctx.output_buffer.stop_output()
            if self.server_ctx.is_server_responding():
                self.cancel_responding()
            return True
        return False

    def stop_listening(self) -> bool:
        if self.server_ctx.listening:
            # stop listening
            self.server_ctx.listening = False
            return True
        return False

    def commit_audio_input(self) -> bool:
        if self.server_ctx.listening:
            self.server_ctx.listening = False
            ce = InputAudioBufferCommit()
            self._send_client_event(ce)
            return True
        return False

    def clear_audio_input(self) -> bool:
        if self.server_ctx.listening:
            self.server_ctx.listening = False
            ce = InputAudioBufferClear()
            self._send_client_event(ce)
            return True
        return False

    def get_session_obj(self, vad_mode: bool) -> SessionObject:
        session_obj = self.conf.get_session_obj(vad_mode)
        session_obj.instructions = self.conversation.get_instructions()
        tools = []
        for fn in self.conversation.get_functions():
            tools.append(fn.to_dict())
        session_obj.tools = tools
        return session_obj

    def create_response(self) -> bool:
        session_obj = self.get_session_obj(self.vad_mode)
        ce = ResponseCreate(
            response=session_obj
        )
        self._send_client_event(ce)
        return True

    def is_server_responding(self) -> bool:
        return self.server_ctx.is_server_responding()

    def is_speaking(self) -> bool:
        return self.server_ctx.output_buffer.is_speaking()

    def receive_server_event(self) -> bool:
        self.logger.debug("start to receive server event")
        data = self.connection.recv(timeout=0.1)
        if data:
            self.logger.debug("got received server event")
            self.session_state.recv(data)
            return True
        return False

    def handle_ghostos_event(self, event: GhostOSEvent):
        # send message to server, let the realtime server handle the new message items.
        for msg in Turn.iter_event_message(event):
            self.add_message_to_server(msg)

    def add_message_to_server(self, message: Message, previous_item_id: Optional[str] = None) -> bool:
        item = MessageItem.from_message(message)
        if item is not None:
            ce = ConversationItemCreate(
                previous_item_id=previous_item_id,
                item=item,
            )
            self._send_client_event(ce)
            return True
        return False

    def _send_client_event(self, event: ClientEvent):
        data = event.to_event_dict()
        self.logger.debug("send client event type %s", type(event))
        self.connection.send(data)

    def respond_error_message(self, error: str) -> None:
        self.server_ctx.respond_error_message(error)
