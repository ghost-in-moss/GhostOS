from __future__ import annotations
from typing import Tuple, List, Dict, Optional, Iterable
from abc import ABC, abstractmethod
from .ws import OpenAIWSConnection
from .configs import SessionObject, OpenAIRealtimeConf
from .event_data_objects import MessageItem
from ghostos.core.messages import Message, MessageType, Role
from ghostos.core.runtime.events import EventTypes, Event
from ghostos.abcd import Conversation, GoThreadInfo
from ghostos.contracts.logger import get_logger, LoggerItf
from ghostos.contracts.assets import AudioAssets, FileInfo
from queue import Queue, Empty
from enum import Enum
from .state_of_server import ServerContext


class RealtimeAppStage(str, Enum):
    CREATED = "created"
    RESPONDING = "responding"


class Context(ServerContext):
    """
    realtime app context
    """

    conf: OpenAIRealtimeConf
    conversation: Conversation
    listening: bool
    thread: GoThreadInfo
    logger: LoggerItf
    connection: Optional[OpenAIWSConnection]
    audio_format: str = "wav"
    response_id: Optional[str]

    stage: str
    status_desc: str

    def __init__(
            self,
            conf: OpenAIRealtimeConf,
            conversation: Conversation,
    ):
        self.stage = RealtimeAppStage.CREATED
        self.status_desc = ""
        self._closed: bool = False

        self.conf = conf
        self.conversation = conversation
        # sync instructions
        # todo: realtime logger
        self.logger = get_logger("OpenAIRealtime", conversation.scope)
        self.thread = conversation.get_thread(truncated=True)
        # todo sync
        self._history_message_ids: set[str] = set(
            item.msg_id for item in self.thread.get_messages(True)
        )

        self.messages_order: List[str] = []
        self.buffer_messages: Dict[str, Message] = {}

        self.connection: Optional[OpenAIWSConnection] = None
        self.error_messages: List[Message] = []

        self.listening: bool = False
        """if the client side shall listen """

        # when realtime server is speaking, the audio bytes shall send through the speaking_queue
        self.speaking: bool = False
        self.speaking_queue: Optional[Queue] = None

        self.response_id: Optional[str] = None
        self.response_queue: Optional[Queue] = None

    def get_session_obj(self) -> SessionObject:
        session_obj = self.conf.session
        session_obj.instructions = self.conversation.get_instructions()
        tools = []
        for fn in self.conversation.get_functions():
            tools.append(fn.to_dict())
        session_obj.tools = tools
        return session_obj

    def send_error_message(self, error: str) -> None:
        pass

    def update_history_message(self, message: Message) -> None:
        pass

    def stop_response(self, response_id: str) -> None:
        pass

    def send_speaking_audio_chunk(self, data: bytes) -> None:
        pass

    def change_stage(self, stage: str, desc: str):
        self.stage = stage
        self.status_desc = desc

    def is_closed(self) -> bool:
        return self.conversation.is_closed()

    def send_err_message(self, error: str):
        message = MessageType.ERROR.new(content=error, role=Role.SYSTEM.value)
        self.error_messages.append(message)

    def update_complete_message_item(self, item: MessageItem, update: bool = True):
        if item.status == "incomplete":
            # incomplete item do not update yet.
            return
        # save audio file
        if item.type == "message" and item.has_audio():
            audio_assets = self.conversation.container().force_fetch(AudioAssets)
            if update or not audio_assets.has_binary(item.id):
                audio_data = item.get_audio_bytes()
                file_info = FileInfo(
                    fileid=item.id,
                    filename=f"{item.id}.{self.audio_format}",
                    filetype=f"audio/{self.audio_format}",
                )
                audio_assets.save(file_info, audio_data)

        message = item.to_complete_message()
        self.update_message(message, update)

    def update_message(self, message: Message, update: bool = True):
        if message is None:
            return
        """
        update the ghostos message to current session.
        """
        if message.msg_id in self._history_message_ids:
            if update:
                self.thread.update_message(message)
            return

        if message.msg_id not in self.buffer_messages:
            self.messages_order.append(message.msg_id)
        if update or message.msg_id not in self.buffer_messages:
            self.buffer_messages[message.msg_id] = message

        if message.type == MessageType.FUNCTION_CALL:
            # 如果是 function call, 需要立刻运行一次同步流程.
            self.sync_ghostos_conversation()

    def sync_ghostos_conversation(self):
        # 1. 检查messages 是否有 function call
        # 1.1 如果 function call 存在, 需要调用 conversation 运行一次 function call
        # 1.2 如果 function call 不存在, 则仅仅更新 thread.
        if len(self.buffer_messages) == 0:
            return
        has_call = False
        messages = []
        for msg_id in self.messages_order:
            if msg_id in self._history_messages:
                # history message exists.
                continue
            if msg_id not in self.buffer_messages:
                self.logger.error(f"Message {msg_id} not in buffered messages")
                continue
            message = self.buffer_messages[msg_id]
            messages.append(message)
            if message.type == MessageType.FUNCTION_CALL:
                has_call = True

        event_type = EventTypes.ACTION_CALL if has_call else EventTypes.NOTIFY
        event = event_type.new(
            task_id=self.conversation.task_id,
            messages=messages,
        )
        if has_call:
            r = self.conversation.respond_event(event)
            with r:
                for chunk in r.recv():
                    # output the new items.
                    self.send_response_chunk(chunk)
            self.thread = self.conversation.get_thread(truncated=True)
        else:
            self.thread.new_turn(event)
            self.conversation.update_thread(self.thread)
            self.thread = self.conversation.get_thread(truncated=True)

        self.reset_history_messages()

    def reset_history_messages(self):
        # reset messages
        self.messages_order = []
        self.buffer_messages = {}
        for message in self.thread.get_history_messages(truncated=True):
            if message.msg_id not in self._history_messages:
                self._history_messages_order.append(message)
            self._history_messages[message.msg_id] = message

    def start_response(self, response_id: Optional[str]):
        if response_id is None:
            self.response_id = None
        elif response_id == self.response_id:
            return None

        if self.response_queue is not None:
            self.response_queue.put(None)
            self.response_queue = None
        if self.speaking_queue is not None:
            self.speaking_queue.put(None)
            self.speaking_queue = None

        # update speaking
        if response_id:
            self.response_queue = Queue()
            self.speaking = True
            self.speaking_queue = Queue()

    def cancel_response(self):
        self.start_response(None)

    def send_response_chunk(self, chunk: Message):
        if self.response_queue is None:
            self.logger.error(f"no response queue for {chunk.msg_id}")
            return
        self.response_queue.put(chunk)

    def close(self):
        if self._closed:
            return
        self._closed = True
        # todo

    def __del__(self):
        pass
