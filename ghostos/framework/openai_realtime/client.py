import base64
from typing import Dict, Optional, List
from ghostos.abcd import Conversation
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.assets import AudioAssets
from ghostos.core.messages import Message, MessageType
from ghostos.core.runtime import Turn, Event as GhostOSEvent, EventTypes as GhostOSEventTypes
from .configs import OpenAIRealtimeAppConf
from .ws import OpenAIWSConnection
from .event_data_objects import MessageItem, SessionObject
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


class Context(ServerContext):

    def __init__(
            self,
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

    def get_responding_id(self) -> Optional[str]:
        return self.output_buffer.get_response_id()

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
        self.output_buffer.stop_response()
        self.listening = False

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
        self.thread.new_turn(event)
        self.conversation.update_thread(self.thread)
        self.thread = self.conversation.get_thread(True)
        self._reset_history_messages()

    def respond_message_chunk(self, response_id: str, chunk: Optional[Message]) -> bool:
        return self.output_buffer.add_response_chunk(response_id, chunk)

    def respond_error_message(self, error: str) -> None:
        message = MessageType.ERROR.new(content=error)
        self.output_buffer.add_error_message(message)

    def save_audio_data(self, item: MessageItem) -> None:
        if not item.has_audio():
            return
        audio_data = item.get_audio_bytes()
        if not audio_data:
            return
        asserts = self.conversation.container().force_fetch(AudioAssets)
        fileinfo = asserts.get_fileinfo(item.id)
        if fileinfo is None:
            fileinfo = asserts.new_fileinfo(
                fileid=item.id,
                filename=f"{item.id}.wav",
            )
        asserts.save(fileinfo, audio_data)

    def update_history_message(self, message: Optional[Message]) -> None:
        if message is None:
            return
        if not message.is_complete():
            return

        if message.msg_id in self.history_messages:
            self.history_messages[message.msg_id] = message
            self.thread.update_message(message)
        else:
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

    def start_response(self, response_id: str) -> None:
        if response_id:
            self.output_buffer.start_response(response_id)

    def is_responding(self) -> bool:
        return self.output_buffer.get_response_id() is not None

    def stop_response(self, response_id: str) -> bool:
        if response_id != self.get_responding_id():
            return False
        self.output_buffer.stop_response()
        return True

    def respond_speaking_audio_chunk(self, response_id: str, data: bytes) -> bool:
        if self.get_responding_id() != response_id:
            return False
        return self.respond_speaking_audio_chunk(response_id, data)


class AppClient(Client):

    def __init__(
            self,
            conf: OpenAIRealtimeAppConf,
            conversation: Conversation,
    ):
        self.conf: OpenAIRealtimeAppConf = conf
        self.conversation: Conversation = conversation
        self.ctx: Context = Context(conversation=conversation, listening=True, logger=conversation.logger)
        self.logger = conversation.logger
        self.connection: OpenAIWSConnection = self.connect()
        self.session_state: SessionState = self._create_session_state()
        self.synchronized: bool = False
        self._closed: bool = False

    def connect(self) -> OpenAIWSConnection:
        self._validate_closed()
        return OpenAIWSConnection(
            self.conf.ws_conf,
            logger=self.ctx.logger,
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
        content = base64.b64encode(buffer).decode()
        ce = InputAudioBufferAppend(
            audio=content
        )
        self._send_client_event(ce)

    def is_listening(self) -> bool:
        return self.ctx.listening and not self.ctx.is_responding()

    def _create_session_state(self) -> SessionState:
        e = self.connection.recv(timeout=self.conf.session_created_timeout, timeout_error=True)
        se = ServerSessionCreated(**e)
        return SessionState(self.ctx, se)

    def synchronize_server_session(self):
        if self.synchronized:
            return
        previous_item_id = ""
        count = 0
        ce = SessionUpdate(
            session=self.get_session_obj(),
        )
        self._send_client_event(ce)

        for msg_id in self.ctx.history_message_order:
            message = self.ctx.history_messages[msg_id]
            self._send_message_to_server(message, previous_item_id)
            previous_item_id = message.msg_id
            self.logger.debug("Synchronizing server session with item %s", msg_id)
            count += 1
        self.logger.info("Synchronizing server session done with item %d", count)

    def cancel_responding(self) -> bool:
        if self.ctx.is_responding():
            ce = ResponseCancel()
            self._send_client_event(ce)
            response_id = self.ctx.get_responding_id()
            self.ctx.stop_response(response_id)
            return True
        return False

    def start_listening(self) -> bool:
        if not self.ctx.listening:
            self.ctx.listening = True
            self.cancel_responding()
            return True
        return False

    def stop_listening(self) -> bool:
        if self.ctx.listening:
            # stop listening
            self.ctx.listening = False
            return True
        return False

    def commit_audio_input(self) -> bool:
        if self.ctx.listening:
            self.ctx.listening = False
            ce = InputAudioBufferCommit()
            self._send_client_event(ce)
            return True
        return False

    def clear_audio_input(self) -> bool:
        if self.ctx.listening:
            self.ctx.listening = False
            ce = InputAudioBufferClear()
            self._send_client_event(ce)
            return True
        return False

    def get_session_obj(self) -> SessionObject:
        session_obj = self.conf.session
        session_obj.instructions = self.conversation.get_instructions()
        tools = []
        for fn in self.conversation.get_functions():
            tools.append(fn.to_dict())
        session_obj.tools = tools
        return session_obj

    def create_response(self) -> bool:
        session_obj = self.get_session_obj()
        ce = ResponseCreate(
            response=session_obj
        )
        self._send_client_event(ce)
        return True

    def is_server_responding(self) -> bool:
        return self.ctx.is_responding()

    def receive_server_event(self) -> bool:
        data = self.connection.recv(timeout=None)
        if data:
            self.session_state.recv(data)
            return True
        return False

    def handle_ghostos_event(self, event: GhostOSEvent):
        for msg in Turn.iter_event_message(event):
            self._send_message_to_server(msg)

    def _send_message_to_server(self, message: Message, previous_item_id: Optional[str] = None) -> None:
        ce = ConversationItemCreate(
            previous_item_id=previous_item_id,
            item=MessageItem.from_message(message),
        )
        self._send_client_event(ce)

    def _send_client_event(self, event: ClientEvent):
        self.connection.send(event.to_dict())

    def respond_error_message(self, error: str) -> None:
        self.ctx.respond_error_message(error)