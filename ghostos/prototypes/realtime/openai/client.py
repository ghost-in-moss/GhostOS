from typing import Dict, Optional, List, Set, Self, Union
from queue import Queue
from ghostos.abcd import Conversation
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.assets import AudioAssets, FileInfo
from ghostos.core.messages import Message, MessageType
from ghostos.core.runtime import GoThreadInfo, Event as GhostOSEvent, EventTypes as GhostOSEventTypes
from .configs import OpenAIRealtimeConf
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
)
from .state_of_server import ServerContext, SessionState
from .state_of_client import Client


class Context(ServerContext):

    def __init__(
            self,
            conversation: Conversation,
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
        self.error_messages: List[Message] = []
        """ errors """

        # status.
        self.unsent_message_ids: List[str] = []
        self.sent_message_ids: Set[str] = set()
        self.response_id: Optional[str] = None
        self.response_queue: Optional[Queue] = None
        self.speaking_queue: Optional[Queue] = None
        self.listening: bool = False

    def _reset_history_messages(self):
        self.history_messages: Dict[str, Message] = {}
        self.history_message_order: List[str] = []
        for message in self.thread.get_messages(True):
            self.history_messages[message.msg_id] = message
            self.history_message_order.append(message.msg_id)

    def _reset_buffer_messages(self):
        self.buffer_message_ids = []
        self.buffer_messages: Dict[str, Message] = {}
        self.unsent_message_ids = []
        self.sent_message_ids = set()

    def update_local_conversation(self) -> None:
        self.stop_response(self.response_id)
        self.listening = False

        buffered = []
        function_call = False
        for msg_id in self.buffer_message_ids:
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

    def send_response_chunk(self, response_id: str, chunk: Optional[Message]) -> bool:
        if chunk is None:
            return False
        if response_id != self.response_id:
            return False
        if self.response_queue is not None:
            self.response_queue.put(chunk)
            return True
        return False

    def send_error_message(self, error: str) -> None:
        message = MessageType.ERROR.new(content=error)
        self.error_messages.append(message)

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
            if message.msg_id not in self.sent_message_ids:
                self.unsent_message_ids.append(message.msg_id)

    def add_message_item(self, item: MessageItem, previous_item_id: str) -> None:
        if item is None:
            return
        message = item.to_complete_message()
        self.update_history_message(message)
        if previous_item_id:
            self_item_id = message.msg_id
            new_buffer_ids = []
            inserted = False
            for buffer_id in self.buffer_message_ids:
                if buffer_id == self_item_id:
                    continue
                else:
                    new_buffer_ids.append(buffer_id)

                if buffer_id == previous_item_id:
                    new_buffer_ids.append(self_item_id)
                    inserted = True
            if not inserted:
                new_buffer_ids.append(self_item_id)
            self.buffer_message_ids = new_buffer_ids

    def start_response(self, response_id: str) -> None:
        if response_id == self.response_id:
            return
        if self.response_queue is not None:
            queue = self.response_queue
            queue.put_nowait(None)

        self.response_id = response_id
        self.response_queue = Queue()
        self.speaking_queue = Queue()

    def is_responding(self) -> bool:
        return self.response_id is not None

    def stop_response(self, response_id: str) -> bool:
        if response_id == self.response_id:
            self.response_id = None
            if self.response_queue is not None:
                self.response_queue.put(None)
            if self.speaking_queue is not None:
                self.speaking_queue.put(None)
            self.response_queue = None
            self.speaking_queue = None
            return True
        return False

    def send_speaking_audio_chunk(self, response_id: str, data: bytes) -> bool:
        if response_id == self.response_id and self.response_id is not None:
            if self.speaking_queue is not None:
                self.speaking_queue.put_nowait(data)
                return True
            else:
                self.logger.error("speaking audio chunk but queue is not exists")
        self.logger.debug(
            "speaking audio chunk of response id %s is not current response %s",
            response_id, self.response_id,
        )
        return False


class AppClient(Client):

    def __init__(
            self,
            conf: OpenAIRealtimeConf,
            conversation: Conversation,
    ):
        self.conf: OpenAIRealtimeConf = conf
        self.conversation: Conversation = conversation
        self.logger: LoggerItf = conversation.logger
        self.ctx = Context(conversation=conversation)
        self.connection: OpenAIWSConnection = self.connect()
        self.session_state: SessionState = self._create_session_state()
        self.synchronized: bool = False

    def connect(self) -> OpenAIWSConnection:
        return OpenAIWSConnection(
            self.conf.ws_conf,
            logger=self.logger,
        )

    def reconnect(self) -> None:
        if self.connection is not None:
            connection = self.connection
            connection.close()
        if self.session_state is not None:
            self.session_state.destroy()

        self.connection: OpenAIWSConnection = self.connect()
        self.session_state: SessionState = self._create_session_state()
        self.synchronized = False

    def _create_session_state(self) -> SessionState:
        ce = SessionUpdate(
            session=self.get_session_obj(),
        )
        self._send_client_event(ce)
        e = self.connection.recv(timeout=self.conf.session_created_timeout, timeout_error=True)
        se = ServerSessionCreated(**e)
        return SessionState(self.ctx, se)

    def synchronize_server_session(self):
        if self.synchronized:
            return
        previous_item_id = ""
        count = 0
        for msg_id in self.ctx.history_message_order:
            message = self.ctx.history_messages[msg_id]
            self._send_message_to_server(message, previous_item_id)
            previous_item_id = message.msg_id
            self.logger.debug("Synchronizing server session with item %s", msg_id)
            count += 1
        self.logger.info("Synchronizing server session done with item %d", count)

    def update_local_conversation(self) -> None:
        # todo: function calling
        self.ctx.update_local_conversation()

    def cancel_responding(self) -> bool:
        if self.ctx.is_responding():
            ce = ResponseCancel()
            self._send_client_event(ce)
            self.ctx.stop_response(self.ctx.response_id)
            return True
        return False

    def start_listening(self) -> bool:
        if not self.ctx.listening:
            self.ctx.listening = True
            self.ctx.stop_response(self.ctx.response_id)
            return True
        return False

    def stop_listening(self) -> bool:
        if self.ctx.listening:
            self.ctx.listening = False
            return True
        return False

    def is_listening(self) -> bool:
        return self.ctx.listening

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

    def is_responding(self) -> bool:
        return self.ctx.is_responding()

    def receive_server_event(self) -> bool:
        data = self.connection.recv(timeout=None)
        if data:
            self.session_state.recv(data)
            return True
        return False

    def _send_message_to_server(self, message: Message, previous_item_id: str = "") -> None:
        ce = ConversationItemCreate(
            previous_item_id=previous_item_id,
            item=MessageItem.from_message(message),
        )
        self._send_client_event(ce)

    def _send_client_event(self, event: ClientEvent):
        self.connection.send(event.to_dict())

    def send_error_message(self, error: str) -> None:
        self.ctx.send_error_message(error)
