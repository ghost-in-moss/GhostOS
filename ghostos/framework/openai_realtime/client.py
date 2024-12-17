import base64
from typing import Dict, Optional, List
from ghostos.abcd import Conversation
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.assets import AudioAssets
from ghostos.core.messages import Message, MessageType
from ghostos.core.runtime import Turn, Event as GhostOSEvent, EventTypes as GhostOSEventTypes
from ghostos.helpers import uuid
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
        ce.session.instructions += "\n*ALWAYS RESPOND WITH AUDIO*"
        self.logger.debug("update session: %s", repr(ce))
        self._send_client_event(ce)

    def synchronize_server_session(self):
        if self.synchronized:
            return
        count = 0
        self.update_session()
        self._hack_openai_realtime_beta()
        previous_item_id = None
        for msg_id in self.server_ctx.history_message_order:
            message = self.server_ctx.history_messages[msg_id]
            if not message.content:
                continue

            ok = self.add_message_to_server(message, previous_item_id)
            if ok:
                previous_item_id = message.msg_id
            self.logger.debug("Synchronizing server session with item %s", msg_id)
            count += 1
        self.logger.info("Synchronizing server session done with item %d", count)
        self.synchronized = True

    def _hack_openai_realtime_beta(self):
        ce = ConversationItemCreate(
            item=MessageItem(
                role="user",
                type="message",
                content=[
                    Content(
                        type="input_audio",
                        audio="EgAXABMAFwAUABgAHQAeAB8AIAAiACMAJgAoACYAJgAmACUAJgAkACIAHQAYABkAHAAcABsAGgAaAB0AHgAeAB4AHAAeAB4AHwAhACEAIAAeAB8AIwAiABwAGQAbABoAGgAYABYAFgATABMAFwAZABcAFgAXABsAIQAhACAAIAAfAB8AIQAhAB0AFwATABIAFAAUABAAEwAQABEAFQAWABgAFwAXABkAHAAeAB4AHQAbABkAHAAbABkAFQAOAAwADgAQAA8ACwAJAAkACwAPAA8ADQALAAoACgAMAA0ACgAIAAgACAAIAAYABQAFAAMABAAFAAYABAABAAIAAwAGAAYABwAGAAIABAADAAYABQAAAP3/+//8//7/+v/3//b/9f/4//n/+v/5//T/9f/6//r/+v/4//b/8//1//f/+f/4//P/8f/w//D/7v/q/+b/5v/n/+n/6v/p/+j/5f/l/+f/6f/r/+b/5//r/+r/6f/n/+b/5f/j/+T/5f/l/+T/4P/g/+D/4P/h/+D/4v/i/+H/4//n/+P/4P/f/97/4P/e/97/3P/b/9v/2P/a/9n/1f/S/9T/2v/b/9r/2P/Z/9n/2f/Z/9z/3P/b/9n/2v/d/9v/2//Y/9f/2f/Y/9z/3f/a/9v/3f/i/+z/7f/s/+//8f/x//L/9P/0//X/9P/2//b/9//3//j/+P/4//n/+P/6//r/+v/6//v/+//7//v/+//8//v//P/8//z//P/8//3//P/9//3//f/8//7//f/9//3//v/+//7//v/+//7//v////7//v/+//7////+//////////7//////////////wAA////////AAAAAAAA//8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD//wAAAAD//wAAAAAAAP//AAAAAP//AAD//wAA//8AAP//AAAAAAAA//8AAAAAAAD//wAAAAD//wAA//8AAAAA/////wAA//8AAP//AAAAAP//AAD//wAA/////wAA/////wAA/////wAA//8AAP////8AAP//AAAAAP////////////8AAP////8AAAAA///////////////////////////+//////////7////+/wAA/v///////v///////////////v////////////7////+///////+/////v/+/////v////7//v////7////+//7////+/////v/+/////v/////////////////////////////////////////+/wAA//////////////////////////////////////////8AAP///////////v///////////wAA//8AAAAAAAD/////AAD/////AAAAAAAAAAAAAAAAAAAAAP////8AAAAAAAD//wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAEAAAAAAAEAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgABAAEAAAABAAAAAQAAAAAAAQABAAAAAQABAAEAAgADAAMAAgACAAIAAgABAAIAAgACAAIAAgABAAIAAgACAAIAAgACAAIAAwACAAMAAwADAAIAAQABAAEAAQABAAAAAAABAAEAAQABAAEAAQABAAIAAQACAAIAAgABAAEAAgACAAEAAQABAAEAAQACAAEAAQABAAAAAAABAAIAAgABAAIAAwACAAIAAwADAAMAAwADAAIAAwACAAIAAwACAAIAAwACAAEAAgACAAIAAgACAAIAAgACAAIAAwADAAIAAgACAAEAAgABAAEAAQABAAIAAgADAAMAAwACAAMAAgADAAQAAwACAAMAAwADAAQABAAEAAUABAAEAAQABQAEAAUABQAFAAQABQAEAAMABQAFAAUABQAFAAUABAAEAAQABAAFAAUAAwAEAAUABQAFAAYABgAFAAcABgAFAAYABgAGAAUABgAGAAcABwAIAAcABAAFAAQAAwADAAMAAgADAAMAAwADAAMABAAFAAYABgAGAAUABQAFAAQABAADAAMAAwADAAEAAQACAAIAAQABAAIAAgABAAEAAQACAAIAAwAEAAMAAgACAAMAAgACAAIAAQACAAEAAgABAAEAAQABAAIAAAAAAAAA/v/+//7//v/9//z//f/8//7//////////v8AAAAA/////wAA//8AAAAAAAAAAP7///////z//f/8//r/+//7//r/+f/6//n/+P/6//r/+v/6//r/+//6//v//P/7//v/+//7//r/+v/5//j/9//3//f/+P/5//j/+v/5//f/+f/3//f/9//3//b/9f/0//T/9P/z//T/9f/0//P/9f/1//X/9P/z//P/9P/1//X/9f/1//b/9f/0//P/9P/0//L/8v/y//L/8f/y//P/8v/y//P/8//y//D/7//u/+7/7P/t/+3/7v/t/+7/7f/s/+z/7P/s/+7/8f/y//P/8//1//b/9P/1//X/8v/w/+3/6//r/+r/6//s/+z/7P/s/+3/7P/t/+//7//w//L/8f/x//D/8f/y//H/8f/x//D/8P/x//H/8v/v/+7/7v/v/+7/7f/u/+//7v/t/+7/7f/t/+3/6v/r/+3/7v/v/+//8f/w/+7/7//x/+//7f/t/+z/7P/t/+z/7v/u/+7/7v/w//D/7//u/+7/8v/y//D/7//y//D/8P/y//H/8v/x/+//7//w/+//8f/y//L/8v/x//H/8f/v/+7/7v/w/+7/7f/u/+3/6v/s/+//7//w//L/8v/x//L/8f/y//H/8P/y//H/7//u/+v/6v/r/+v/6v/t/+7/7P/u/+7/7f/w/+7/7f/v/+7/7P/r/+v/6//q/+v/6f/o/+r/6v/r/+3/7v/r/+n/6v/q/+f/6f/m/+X/5f/l/+b/5v/o/+r/6//r/+z/7f/r/+v/7v/t//H/8f/x//T/9P/y//P/9P/0//T/9P/z//b/9f/z//L/8//y//D/7f/r/+v/7P/s/+3/7//w//P/9P/2//n/+f/5//v/+f/5//n/9v/4//r/+//7//3//P/9//v/+v/8//7//v/+//3//P////7///8AAAMABAAFAAcABAADAAMAAwAFAAUABwAIAAgABwADAAIAAQACAAIAAwABAAIAAQABAAAAAwAGAAoADAANAAwACQAHAAgABwAKAA8ADQANAA0ADQAMAAsACwAMAA4ADgAPABEAEQARABUAFgAVABYAFgAXABQAEQASABEAEQASABIAEAAPABEAEAASABYAGQAZABkAGQAVABYAFgAXABoAGQAaABkAFwAVABUAFAAVABcAGAAYABgAFwAXABcAGQAaAB0AHgAeAB8AHwAcAB8AHQAdAB4AHwAeABwAHQAcAB0AHQAbABsAGwAbABwAGgAYABkAGQAbABsAGwAbABoAGwAaABkAFwAaABoAGwAbABkAGAAZABgAFwAYABUAFQAWABUAEgATABQAFAATABMAFAATABIAEwATABIAEgAVABQAFAATABIAFQAUABYAGQAYABgAGAAWABMAEgAVABUAEwATABMAEAAQABAADwAMAAoACgAJAAwACwAMAAwADAANAAsADAALAAsACgAKAAoACAAGAAQAAQABAAMABQADAAUABQAFAAcABgAGAAYABQAEAAUAAwACAAMAAgACAAQAAwADAAUABQABAAEAAgAEAAMAAwADAAMAAQABAAIAAAAAAAEA///+//v/+v/3//X/9P/z/wUABgAFAAUABQAFAAQABQAFAAcABwAFAAYACAAGAAUABAAFAAUABQAEAAMAAgAAAAAAAAAAAAIAAgAAAAEAAQABAAAAAAAAAAEAAAAAAAAAAAABAAMAAgABAAEAAQABAAAAAAACAAAA//8AAAAA///9//7//f/9//z//P/8//r//P/7//v/+//7//r/+//9//z//f/+//7//v/9//3//f/9//r/+P/6//n/9//2//b/9f/0//T/9f/2//b/+P/7//f/9//4//n/+f/5//j/+P/5//v/+//6//v/+v/5//n/+P/0//L/8v/x//L/8f/y//H/8P/w/+//8P/y//D/8v/y//P/9P/z//L/8P/y//L/8P/y//P/9P/0//X/8//z//L/8f/x//H/8v/w//D/8P/t/+7/7v/s/+z/7f/t/+r/7P/s/+3/7//v//P/8//z//P/9P/z//L/9P/y//P/8v/x//H/7v/t/+z/6//t/+7/7f/v/+7/7f/v/+7/7v/v//D/8v/y//H/9P/0//P/8v/w/+//7//w/+//7//w//D/8v/y//L/8P/w//D/8f/x//H/8P/w//D/8P/y//P/8v/y//D/7v/v/+//8v/z//P/9P/y//P/8v/z//T/8//z//T/9f/1//P/9P/2//X/9f/2//f/9v/4//j/9//2//f/9//5//r/+v/6//r/+v/7//r/+P/5//n/9//3//b/9v/0//b/+P/7//v//P/9//7//f/9//7///8AAAAAAQABAAAAAAD///7//P/7//3/+//9//3//P/9//3//P8AAAAAAQABAP///v/+//3///8AAAAAAAAAAAEAAgACAAQABQAGAAUABQADAAMAAwAAAP//AAD///7/AQACAAIAAwACAAIAAAABAAIAAQAAAAMABAACAAMAAwAEAAIAAQABAP///f/+//////8AAAAAAAABAAIAAgADAAQAAwAEAAMAAgADAAIAAQACAAMAAgAFAAIAAAADAAEAAQADAAIAAAAAAAAAAgADAAMABQAFAAcABwAGAAcABQAFAAQAAgACAAEAAQABAAEAAQADAAEAAQAAAAAAAAADAAQABQAGAAcABQAFAAYABwALAAsACgAKAAkACAAHAAYABgAHAAYABgAIAAkACQAKAAsACwALAAwADQANAA4ADwAPAA0ADAAKAAoACQAJAAoADQALAA0ADQAMAAwADAAOAA4ADgAPABEAEAARABIAEgARAA8ADgANAA4ADAAJAAgACAAIAAoACwALAA0ADAAMAA4ADwAOABAAFAAVABcAFgAVABQAEgASABMAEgASABAAEQARABEAEAARABAADwARABMAFQAWABcAFwAXABYAFQAUABMAEQARAA8ADwAOAA4ADgAQABEAEgATABMAEwATABEAEAARABAADwAQABAAEAAOAA0ACwAJAAUAAwAEAAQABQAFAAcACAAMAA4AEAAPAA8AEQAQABAAEAAOAA0ADAALAAoACAAIAAkACAAIAAgACAAHAAYABQAFAAYABgAHAAkACQAIAAgABQAEAAMAAwABAAAAAAAAAAEAAAAAAAEAAQABAAEAAgABAAEAAAAAAP///v8AAAAA/v8AAAAA//////3//f/7//r/+//7//z/+//9//3//P/7//v/+f/6//n/+P/3//b/9//2//T/8v/y//P/8f/x//L/8v/1//b/9P/0//T/8v/z//T/9f/0//T/9//2//T/9P/z//L/8v/y//P/8v/0//T/8//z//H/8f/v//H/8f/x//L/9P/2//b/9//2//P/8//y//L/8v/x/+//7v/u/+3/7f/u/+//8v/z//T/9P/1//X/9P/1//X/9P/0//T/9P/z//L/8P/w//D/7//u/+7/8P/w//D/8f/x//L/8v/y//H/8//y//H/8f/v/+//7v/u/+7/7P/r/+3/7//u/+7/7f/u//H/8P/w//L/8//0//T/9P/1//P/8//z//H/8P/v/+3/7P/s/+v/6//r/+3/7f/v/+//8P/y//L/8v/0//T/8//1//T/8//z//P/8v/y//H/8f/x/+//8f/w//H/8P/x//H/8f/x//L/9P/1//X/9f/0//T/8//y//L/8f/y//H/7//v//D/7v/u/+3/7f/u/+//7//x//P/8//2//f/+P/5//r/+f/4//n/+v/2//T/8//y//H/8f/x//H/8f/y//T/9P/0//b/9v/3//j/+P/6//j/+f/5//n/+P/4//j/+P/3//f/+f/4//n/+v/6//v//P/+//7//v////7//v/+//7//v/+//7/AAABAAIAAgABAAEAAAAAAAAA///+//7//f/8//3///8AAAIABAAFAAcABwAHAAcABgAGAAYABgAFAAQABQAEAAUABAADAAUABQAGAAgABwAIAAgACQAJAAgABwAHAAcACAAHAAkACQAIAAkACgALAAsACwALAAwADAALAAsACgAHAAcABwAGAAUABwAHAAcABwAIAAcACgAIAAcACAAKAAkACQALAAsACwALAAwADAALAAwADAAKAAoACgAIAAcABwAGAAYABgAHAAcACAAIAAoACQAJAAgACAAHAAYABwAHAAcABgAHAAgACAAJAAgACQAIAAkACQAJAAcACAAIAAgABwAHAAcACAAHAAYABgAFAAMABAAEAAUABAAGAAYABgAFAAYABgAGAAYABgAFAAcABgAFAAcABgAFAAQAAgABAAEAAQABAAEAAQAEAAUABAAFAAQABAAEAAMABAAEAAMABQAHAAYABwAJAAcABwAJAAYABAADAAIAAgAAAAAAAAAAAAAAAAACAAEABAAEAAQABQAHAAcACAAHAAUABgAGAAYABwAGAAUABAADAAUABQAEAAUABQAFAAIAAgACAAEAAQAAAAEAAwADAAQAAgADAAMAAwACAAIAAgACAAEAAQACAAAAAwAFAAQABAAGAAcABwAHAAcABgAGAAYABgAFAAUABQAFAAUABgAGAAgABwAIAAcABgAFAAQAAgABAAAAAQAAAAAAAgAAAAAAAAABAAEAAQACAAMABAAEAAMAAwAEAAUABAAFAAQABAAEAAIAAAAAAAAAAAAAAAAAAAD//////f/+/wAA//8AAAAAAAABAAIAAwAEAAMABAAGAAQAAwAGAAYABQAGAAUAAwADAAMABAADAAIAAQABAAEAAQAAAAAAAgABAAEAAQAAAAAAAAD+//7//f/9//z//P/8//7//v/+////AAAAAAEAAQABAAAAAAABAAAAAQABAAAA//8AAAAA//8AAAAAAAABAAEAAgABAAAAAAAAAAAAAAABAAAAAAAAAAAAAAD+//////8AAAAA///////////+//3//v/+////AAAAAAEAAgAEAAQABAAFAAcACAAHAAYABwAGAAUABAAEAAQABAABAAAAAAD+/wAAAQAAAAEAAAAAAAAA////////AAD9////AAD+/wAAAAD///7//v/+//3//v//////AQAAAAEAAgAAAAEAAQABAAMABAAFAAUAAwABAAIAAAAAAP///f/8//v/+f/6//v/+f/4//n/+v/7//z/+//8//z//v/8//7////+//3//f/8//v//P/8//z/+v/7//3//f/9//z//f/7//v//f/8//z/+v/3//j/9//3//f/9f/0//T/8//1//T/9P/2//b/9v/1//b/9v/0//X/9//1//b/9f/z//P/8v/x//L/8P/w//D/8f/w/+//8P/w/+//7//u/+7/7//s/+z/7v/t/+//7v/s/+//7f/r/+3/7P/u/+//7v/t/+//7f/s/+z/7P/r/+z/6v/r/+v/6v/r/+r/6v/q/+v/6//q/+v/6//s/+3/7v/w//D/8f/z//L/8f/y//P/8//z//P/8v/0//T/8//0//X/9v/2//X/9f/1//T/8//z//T/8f/y//P/8v/y//P/8//z//L/8v/z//T/8//y//L/8v/y//T/9P/0//P/9P/2//f/+P/4//r/+v/8//z//f/8//3//P/8//3/+v/5//n/+v/7//v/+//7//z//v8AAAMABQAGAAcABgAIAAYABgAFAAUABAACAAIAAAAAAAAAAAAAAAAAAAAAAAEAAAADAAMABQAGAAcABwAIAAkACgAJAAgACAAIAAcACAAGAAYABwAHAAgABwAHAAoADAANAA8ADgARABEAEQATABEAEAAOAA8ADwAPAA0ADAALAAkACQAIAAkACQAJAAsADAAOABAAEAARABIAEQARABAAEgATABEAEQARABIAEwASABMAEwARABIAEgASABEAEwARABEAEgARABMAEgARABEAEAAPABAAEAAQAA8ADgAOAA8AEAAPABIAEwATABQAFQAUABUAFQAVABcAFgAYABcAFwAWABQAFAASABEAEQAQAA0ADQAOAA0ADwAOAA8ADwAOABEAEQARABMAEwATABMAEQASABEAEAAPAA4ADgAMAAwADAALAAoACgALAAsADAAKAA0ADwANAA0ADgAOAA0ADAAMAAwACwALAAsACgALAAsACgALAA0ADQAMAA0ADgAOABAAEQASABMAEwATABIAEgAPAA0ACwAJAAcABwAGAAYABgAGAAcACAAIAAoADAANAA0ADAALAAwADQAMAAwACwAJAAgABwAGAAYAAwACAAMAAgADAAMAAwAFAAcABwAIAAkACQALAAsACgAKAAoACQAJAAcABwAIAAcACAAHAAcACAAIAAgACAAGAAYACAAJAAoACQAKAAkACQAIAAgABQAGAAQAAwABAAAA/f/8//z/+//8//3//P/+//7//f/+////AAABAAEAAgAAAAEAAwACAAEAAgABAP///v////7//v/+/////////wAA/v8AAAAAAAABAAAA/v////7//v/8//v/+//6//v/+f/5//r/+v/5//j/+P/4//j/+v/7//v/+//9//3//f/+///////+/////f/8//v/+f/5//n/+f/5//n/+f/4//b/9v/2//j/+P/5//v//P/9//z/+//7//r/+v/4//f/9//3//b/9P/1//T/8//z//T/9P/0//f/9//2//b/9//3//f/9v/2//b/9f/0//T/9f/4//f/+P/4//j/+//9//v/+v/7//r/9//2//b/9//3//n/9//3//f/9v/2//b/9v/2//X/9P/3//j/+P/4//f/9//2//X/9P/2//b/9v/2//b/9f/2//j/9//2//b/9v/3//b/+P/4//f/+P/4//j/+P/3//f/+P/4//j/+P/5//j/9v/3//f/9P/3//j/9v/4//r/+//6//v/+//6//n/+f/6//n/+v/6//n/+f/5//r/+//7//z//v////7///////7//v/9//z////9//v//P/7//r/+f/3//f/9//2//f/9//1//j/+v/7//r/+//9//3///8AAAAAAAAAAAAAAAAAAP///v/7//r/+//5//j/+P/5//j/9//6//v/+v/7//3//f/+/////f///wAA//8AAP/////8//z/+v/5//n/+v/7//v//P/9//3///8AAAAAAAAAAAAA//8AAAAAAAAAAAAA//8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//AAD//wAAAAAAAAAA///+//7//P/7//z/+//8//z//v//////AAAAAAEAAgADAAIAAAABAAAAAAD//wAAAAAAAAAAAAAAAAAAAAABAAEAAgACAAAAAQACAAEAAgACAAEAAgACAAEAAgAEAAQABQAFAAYABQAGAAMAAgABAAEAAAD+//3///8AAAAAAAAAAAEAAgABAAIABQAFAAMABQAFAAQABQAFAAIAAQABAAAA///+/wAAAgACAAIAAwAFAAYABQAHAAcABwAIAAcABQAFAAMAAwABAP//AAABAAAA///+////AAAAAAEAAwAEAAQABAAEAAQABAAFAAMAAgABAAEAAgAAAAEAAgACAAMAAgABAAEAAQAAAP///f/9////AAABAAMAAgADAAQABAAGAAQABAADAAIAAwACAAIAAwABAAEAAQAAAAAAAgABAAAABAAFAAYABwAGAAYABgAGAAYABgAGAAYACAAFAAYABgAFAAUABgAGAAUABQAHAAYABQAFAAUABQAEAAUABgAGAAUABQAEAAUABAAEAAMABAAFAAQAAwAFAAMAAwAEAAQABAACAAMAAwABAAIAAgABAAMAAgADAAMABAAEAAUABgAFAAUABgAHAAUACAAHAAcABwAGAAcACAAHAAoACAAHAAcABwAHAAcABwAHAAcABwAGAAgACAAHAAgACQAIAAoADQAMAAoADAANAA0ADAALAAgACQAJAAgACAAHAAoACQAIAAoACgAJAAsACwAKAAwADQANAA0ADAAKAAkACQAIAAkABQAFAAYABgAGAAcABgAFAAQABgAGAAYABgAJAAkACgALAAoACgAJAAkACQAJAAcABgAGAAYABQAGAAYABgAIAAkABgAFAAYABgAHAAYABgAHAAkACgAJAAkACgAKAAoACgAJAAgABwAGAAYAAwADAAQABAAEAAUABQAEAAUABAAEAAUABQAEAAQAAwACAAIAAgAAAAAA///+////AAABAAEAAwAEAAQABAAEAAMAAgACAAMAAQAAAAAAAAD///7///////3//v////7//v8AAAEAAQACAAIAAgACAAMAAwAEAAEAAAD/////AAD+//3//P/9//3//f/9//3//f/+/wAAAAABAAEAAQACAAMABAADAAMAAgAAAAAA///+//7//v/9//7////+//7//v/+//////////7///8AAAAA/v/9//7//v/+/wAA/////wAAAAAAAAAA//8AAP///v/8//3//P/8/////v/9/////f/7//3//f/9//7//f///////v///////v////7//v/9//z/+//6//r/+v/7//j/+P/4//j/+f/5//v/+//8//3//f/8//3//f/9/////v/+/////v/9//7//f/8//z//f/+//r/+P/4//j/9//5//f/9v/3//n/+v/8//z//P/6//r/+//6//v/+v/8//z/+P/4//j/+f/3//f/+f/4//f/+f/7//v/+v/7//z//P/6//r//P/7//v/+//6//n/9//2//f/9P/z//T/8P/v//H/9P/y//T/9//2//n//P/7//v//P/8//z//P/4//b/9v/2//T/9P/y//P/8P/w//H/8P/w//H/8//0//X/9v/3//n/+v/8//v/+//6//z//f/6//r/+v/5//f/+f/5//n/+v/7//v/+//9//7///8AAAIAAwADAAMAAQD///7//v/9//3//v/8//7//v///wEAAAAAAAEAAAAAAAAAAQACAAQAAgADAAMAAQAEAAQAAgADAAQAAwABAAIAAQAAAAIAAgABAAEAAAAAAAEAAAACAAIAAgAEAAMABAAEAAMABAACAAIAAAABAAMAAgACAAIAAQABAAIAAgADAAYABgAHAAYABQAHAAcABgAGAAQABAADAAMAAwADAAMAAwAFAAQAAgAEAAQAAwAFAAQABAAFAAUAAwADAAUABAAFAAQABQAEAAMAAwADAAIAAAAAAAAA//8AAP//AAABAAEAAwAEAAUABgAFAAUAAwAEAAMAAwACAAEAAQAAAAEAAQABAAIAAQAAAAEAAAAAAAMAAwABAAEAAgAAAP//AAAAAP3//v////z/+//6//n/+//9//3//f/8//z//f/+/wAA/v/8//3//P/9//z//P/8//v/+//6//v//P/7//r/+v/7//r/+//7//r/+f/5//n/9//4//j/9v/2//j/+P/3//n/+v/6//r/+f/5//n/+f/6//v/+v/6//z/+v/5//r//P/+////AAAAAAEAAAAAAP3//v////z/+//6//r/+//6//z/+//8//z//P/9//3//v////7///8AAP///v/9//3//P/7//v/+f/6//z//f/8//7//v/+/////v/+//7////+//7//v/////////9//3//f/7//v/+v/8//z//P/8//z//v///wAAAAAAAAIAAQAAAAAA///+//3//f/9//v/+//6//n/+f/5//v/+v/6//v/+//6//v/+//7//z//f/8//3//P/9//z/+//5//n/9//3//f/9//1//P/8f/w//D/8v/y//P/9f/2//T/9f/4//f/9f/1//T/8v/w//D/7v/u/+7/6v/p/+r/6v/q/+z/7P/s/+z/7f/t/+3/7P/t/+r/6v/p/+f/5//n/+f/6P/n/+f/5//n/+f/5v/k/+P/4//h/+L/4f/g/+D/4v/h/+P/4//j/+H/4f/j/+H/4P/g/+H/4f/g/+D/4f/g/+D/3//g/9//3f/e/+D/3v/f/+L/4v/j/+P/4v/i/+L/4v/i/+D/4f/g/+D/3//f/9//3//f/9//4f/i/+P/5P/l/+X/4//k/+T/4v/k/+T/5f/l/+b/5//o/+n/6f/r/+z/7f/u//D/7//u/+7/8f/w//D/8v/z//P/9P/z//X/9f/0//X/9v/2//j/+v/6//v//f////3//v8AAP7//v///wAAAAAAAAAAAQD//wAAAAABAAAAAAACAAIABAAGAAkACgALAAsACwALAAsADQANAAoACQAKAAkACgAJAAoACwAMAAwADwASABIAFQAXABgAFgAXABcAFQAUABUAFAASABMAEwATABMAFQAWABcAFgAVABYAFwAVABYAFwAXABgAFwAXABgAGQAYABgAGgAbABwAHgAeABwAGwAcABsAGQAYABcAFwAYABgAGgAbABwAHQAeAB8AHQAdAB8AHAAcABsAGwAZABoAGgAaABoAGQAYABoAGQAYABkAGQAbABsAGwAbABwAGwAdAB0AGgAaABoAGwAbABwAHAAcABsAGgAaABkAGQAYABYAFAAUABUAFAAUABUAFQAXABgAGAAZABcAGAAYABcAFwAWABUAEwAUABQAFQAWABcAFwAYABcAFwAZABkAGgAcAB0AHgAbABwAGwAZABkAGgAaABkAGgAZABkAGQAZAB0AGgAXABgAGQAZABkAHAAdAB8AHwAfACAAIAAgACAAHwAgAB4AHQAeABwAHgAeABwAHgAeAB4AHgAdABwAHgAdABsAGwAbABgAGgAaABoAGwAbAB0AHgAeAB4AHwAhAB8AHgAcABoAGgAZABkAGgAbABoAGQAaABoAGgAaABwAHAAaABkAFwAWABQAEgARABEADwAPABAAEAAPABAAEQARABIAEgARABEAEQASABEAEQAQAA4ADQAMAAsACQAIAAgABwAFAAUABQAFAAUABQAFAAUABQAGAAYABgAFAAQABAADAAEAAAD///3/+//6//j/+f/3//j/+f/5//j/+//7//v//P/7//v/+v/5//f/9v/2//T/8//z//L/8v/x//D/8P/w//D/7v/v/+//8P/v/+7/7P/s/+v/6f/q/+j/6P/n/+X/5f/m/+X/5P/m/+b/5v/m/+T/5P/i/+P/4//i/+T/4v/i/+L/4f/h/9//4P/h/+D/4f/g/+L/4v/h/+L/3//g/+L/4v/g/97/3v/d/9z/3P/b/9r/2v/c/93/3v/e/9//3//f/+H/4//h/+L/4//h/+H/4P/e/97/3//c/9//4P/f/+H/4v/k/+T/5f/l/+X/4//k/+P/4//i/+L/4//j/+T/5P/l/+T/5v/m/+X/5P/k/+L/4//k/+b/5v/m/+j/6f/o/+n/6//q/+z/7f/u/+//7//u/+7/7v/v/+//8P/w/+//7//u/+7/7//v//D/8f/y//L/9P/1//f/+P/3//f/9//5//j/9//3//f/9//4//n/+P/4//j/+//5//r/+//8//z//P/9//3//v8AAAAAAAAAAAAA///9//7//v/+//3//v/+//7//v/+//7//v/+/////f/9//7//v/+//////////7//v///wAAAAAAAAIAAgACAAMAAwAEAAQABAAEAAYABgAFAAQABAAEAAIAAgADAAUABAAEAAQABAAFAAYABAAGAAkABwAJAAoABwAIAAgABwAJAAgACQAIAAcABgAHAAkACQAJAAkACgAMAAsADAALAAwACwALAA0ADAAOAA8AEAASABMAEwARABEAEQAPABAAEAANAA0ADQAMAA4ADwAPABAAEQARABAAEQAUABQAFAATABUAFwAUABMAFAAUABQAFAATABMAFAAUABQAFQAWABcAGQAaABoAGgAZABsAHQAcABsAGwAbAB0AHQAcAB0AHAAbABsAGgAaABsAGgAWABgAGAAWABYAFgAVABYAFwAYABgAGQAaABsAHAAbABkAGAAXABYAFQASABIAEgASABMAFAAVABQAFgAXABgAGQAaABwAHAAcAB4AHQAbABoAGgAaABgAGgAaABoAGQAaABkAGgAbABkAGAAZABgAFwAYABgAFwAZABkAGAAYABkAGgAaABoAGgAbABoAGAAZABcAFwAWABUAFQATABIAEQASABMAEwASABQAEwATABMAFAAVABMAEgASABAADwAPAA4ADwAPAA0ADgANAAwADQALAAsADAAMAA0ADQANAA8ADAAMAA0ADAALAAsACgAIAAoACQAIAAkABwAHAAYABwAHAAcABwAIAAsACQAJAAwACwALAAsACQAIAAgACAAIAAgABwAHAAgABwAGAAcACAAKAAwACwANAA4ADQANAA0ACwAMAAsADAAMAAwADAANAA0ACwALAAoACQAIAAcABgAHAAkACAAKAAwACQAJAAoACQAHAAYABgAEAAQABAAEAAQABQAEAAQABQACAAIAAQAAAP////8AAP7//f/+//z//f/8//r/+//5//r/9//1//X/8//y//H/8f/w//D/7v/v/+//7v/u/+7/7v/t/+7/7P/s/+z/6//q/+r/5//l/+X/5f/j/+H/4f/h/+H/3//f/9//3v/e/97/3//e/93/3v/c/9v/3P/Z/9r/2f/Z/9r/2v/a/9v/3f/d/97/4P/h/+L/4P/g/+D/3//e/9//4P/f/97/3v/f/+D/4P/i/+P/4//i/+T/5P/l/+X/5v/l/+X/5v/m/+b/6P/p/+j/6P/n/+n/6P/m/+X/5v/m/+b/5//o/+j/6P/p/+j/6P/p/+n/6P/o/+j/6P/m/+X/5v/m/+T/5f/m/+T/5P/k/+X/4v/j/+P/4//j/+L/4f/h/+L/4f/j/+H/4v/j/+P/4//k/+X/5f/k/+T/4//i/+H/4P/f/+H/4f/g/+L/4f/h/+P/5P/k/+X/5//q/+n/6f/o/+n/5//n/+f/5v/n/+j/5//o/+j/6f/o/+j/6f/q/+z/7P/r/+z/7v/t/+3/7f/v/+//7//v/+//7v/u/+//7//x//P/8//z//P/9P/0//T/9f/1//X/9f/2//f/9//1//j/+v/6//z//P/7//r/+f/4//n/+//8//v/+v////7//f///wAAAAABAAAAAgAEAAIABAADAAIAAwADAAEAAwADAAIAAwABAAIAAwABAAAAAAABAAIAAAABAAEAAAAAAAAAAAD//////P/7//v/+//7//j/+f/6//r/+P/5//n/+f/4//f/+f/4//f/+P/4//j/+P/4//n/+P/4//r/+v/4//j/+P/2//X/9P/z//H/8v/y//L/8//0//L/8//1//X/9v/2//X/9//4//j/+f/7//3//v/9/////v/+/wAAAAABAAIAAwAFAAYABgAHAAkACAAJAAwACgAIAAoACQAIAAkACwANAA4ADgARABEAEwAUABYAFgAWABcAFwAXABcAFwAXABcAFwAXABgAFgAYABkAGQAbABsAHAAeAB8AIAAhACAAIAAiACEAIgAhACEAIQAgACEAIQAhACEAIgAhACEAIQAgACEAIgAiACIAIgAjACMAJQAlACUAJwAlACQAIwAjACQAIgAiACAAIAAeAB0AHQAbABsAHAAcAB0AHAAdAB0AHAAcAB0AGwAbABwAGQAXABcAFAASABAADgANAAsACQAJAAoABwAGAAcABQAEAAQABAAGAAQAAwAEAAEAAAAAAAAA//////7//f/6//r/+//5//v/+//5//v/+//7//z//P/8//3//v/9//z//P/8//7//f/8//3//f/8//7//f/+/wAA//8AAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAABAAQAAwAEAAYABwAJAAoACgALAA0ACwAMAAwACgAIAAcACAAIAAgACgAIAAgACgAKAAwADAAMAA4ADwAOAA4ADwAPABAADQAPAA4ADAANAAsACQAIAAcABwAGAAYABQAGAAcABgAHAAkACAAKAAoADAAMAAsADQAMAAkACAAIAAcABgAGAAQAAwADAAMAAgACAAMAAwACAAMAAwADAAQAAwAFAAUABAAEAAMAAgABAAIAAgAAAAAA//8AAAAAAAAAAAEAAQABAAAAAAAAAAIAAAABAAIAAgABAAEAAwABAAEAAQAAAAIAAgADAAIAAwABAAQABAAEAAQABgAGAAUABgAHAAYABwAHAAYABwAGAAUABgAEAAMABQADAAQAAwAFAAYABwAIAAkACAAHAAcABwAGAAcACAAHAAcABwAIAAcABgAGAAUABAAFAAMAAwADAAUABwAJAAkACAAHAAgACAAIAAcACAAFAAUABQADAAAAAAD//wAAAAAAAAAAAAAAAAAAAAAAAAAA//8AAP///v/9//7//f/7//v/+//6//n/+P/4//n/+P/4//j/+f/5//f/9//3//b/9//3//f/9v/1//T/8//y//H/8f/y//H/8v/w//D/7//w/+7/7//w/+//8P/v/+7/8P/v/+7/7f/s/+3/6//q/+v/6//p/+n/6f/p/+n/6f/p/+v/6v/r/+3/6//s/+3/7f/t/+r/6f/q/+j/6P/o/+j/6P/m/+j/5//o/+n/6f/p/+j/6P/q/+z/7f/v//D/8f/x//D/8P/u/+z/6//q/+v/6v/p/+j/6f/n/+f/6P/p/+v/7P/r/+3/7v/v//D/8f/x//P/8v/y//L/8P/x//D/7//w//H/8f/x//H/8f/0//T/9P/0//T/9P/0//L/8//1//X/9P/0//P/8v/z//H/8//0//P/9P/0//X/9v/0//P/9v/3//X/9v/4//f/9//3//X/9v/3//b/9//1//X/9P/1//b/9f/2//X/9v/1//X/9P/1//b/9//3//f/9f/2//f/9v/3//b/9//3//f/+f/4//j/+f/5//n/+P/6//r/+//6//z/+//6//z///8AAAAAAAABAAIAAgABAAIAAwAEAAQABQAFAAUABwAIAAgACQALAAwADAANAA8AEQAQABAAEQARABIAEwATABQAFQATABQAFAATABUAFQAUABYAFwAWABcAFQAVABYAFwAXABkAGgAYABoAGgAZABoAGwAaABoAGgAaABsAGQAZABkAGQAYABgAFwAXABcAFwAYABkAGQAZABgAGAAYABkAGgAZABoAGgAYABgAFwAXABYAGAAXABgAGAAXABYAFQAWABMAFAAVABUAFgAUABUAFQAVABUAFQAUABQAFQAVABUAGAAXABcAFwAWABcAFAAVABUAFAAVABYAFQAWABYAFQAVABQAFAAUABUAEwASABMAEwATABMAEwATABQAFAAUABYAFgAWABYAFQAUABEAEAAPAA8AEQARABIAEgATABUAFgAXABYAFwAXABgAGQAXABgAGAAYABcAGAAVABQAFQAUABUAFQAUABUAFAAUABYAFgAXABcAGAAYABkAFwAXABUAFAATABIAEgASABIAEgASABAAEQASABMAFAASABAADwAOAAwADQANAAwACgAJAAwADwANAAsACwAKAAsACQAHAAkABgAFAAMAAgAAAP/////+//z/+//7//v/+v/5//v/+v/6//7//f/9//3//f/9//z/+v/5//j/9f/1//T/8f/x//D/7//w//H/8v/z//P/8//z//L/8f/w//H/8v/z//T/8//y//H/7v/u/+z/6//s/+v/6//t/+7/7//v/+//8f/y//H/8f/x//H/8P/w/+//7f/s/+z/6f/p/+r/6v/q/+v/6//p/+3/7P/t/+z/7P/u/+7/8P/w//L/8v/x/+//7f/t/+7/7v/w//L/8v/x//P/8//w//D/7v/s/+r/6//r/+z/7f/v/+7/7//x//P/8v/x//H/8P/u/+3/7v/v/+3/7f/s/+r/6v/r/+z/6//q/+n/6P/k/+P/5P/l/+X/6P/r//D/8P/x/+//7//v/+z/6//t/+z/7P/r/+n/5//m/+b/5//m/+j/5//m/+T/5f/o/+j/5//n/+f/5//p/+j/6//t/+3/7P/q/+j/5v/j/+P/5f/n/+v/7v/w//D/7//v/+//8P/y//T/9//6//v//P/9//r/+f/5//n/+f/8//3//P/8//r/+f/5//v//v8BAAIAAgACAAAA/////wAAAgAEAAcACAAIAAgACAAIAAgABwAHAAcABgAGAAoADQAMAA8ADwAKAAUAAgAAAAAAAgAFAAYABwAHAAUAAgAAAAIABQAFAAcACAAEAAIAAAD9//3////+//7//f/7//r/+f/3//b/9v/0//X/9v/2//f/9v/4//X/8f/w/+//7//y//X/+f/6//n/+P/1//P/8P/x//L/8f/w/+7/7v/s/+3/8f/0//f/+v/7//r/+v/8//v/+v/7//r/+v/5//b/9v/1//b/9//5//f/9f/0//X/9P/z//L/8//0//X/9//6//z//f/6//n/+P/6//r/+v/7//r/+f/6//7/AQAFAAcABAABAAAA//8AAAMABgAGAAMAAQD+//3/AAAFAAoADAAKAAQAAAD+/wAAAwAIAA0ADwAMAAgABAABAAEAAgADAAYABQACAAAA/v/+////AgAFAAQAAwADAAAA//8AAAEAAwAFAAQABAADAAQABAAEAAYACgALAAwACgAIAAUAAwADAAYABQAGAAUAAgABAP////8AAAEABAAGAAcABwAGAAUAAgAEAAMABAAHAAYABwAFAAQABAAEAAUABAAGAAQAAwACAAEAAwAEAAUACAAKAAkACAAJAAoACgAJAAkABwAHAAMAAAAAAAAAAAABAAQABgAKAAkACAALAAwADgAOAA4ACwALAAkACAAKAAoADAAOAA4AEAARABIAEAAPAA4ADQAPABEAEwARABAAEAASAA8ADAAMAAoACQAHAAkACQAKAAkABgAFAAgACQAIAAgACgAJAAcABgAIAAkACAAGAAcACAAIAAYABAACAAAA//8AAAQABgAGAAcACAAKAAgABQACAAIAAAAAAP//AAABAP//+v/5//z/AQACAAAAAAD///7//f///wAABAAGAAQAAAAAAAEABQAHAAgABQAAAPv/+v/7//v/+//+/wAAAAD//wAABAAEAAMAAgACAAMABgAIAAkADQAPAA8ADwAPABMAFQATABAADQAMAAoACQAIAAQABQAHAAYABwAKAA4ADwAOAAsACgAKAAgACQAKAAoACgAJAAoADAAJAAcACgAOABIAFQAUABEADwATABUAFQAYABcAGQAZABUAGgAeABwAFwAVABUAFgAVABUAFQAUABEADQAOABIAEwAVABYAHQAgABwAGAATABEADgAPABUAGwAbABYAEwASABgAHgAiACIAIQAeABYADwAQABIAFQAYAB4AIQAgABoAEwANAAoACAALAA8ADgAKAAoABAABAAIADQAYABcAEAAJAAUACQALAA8AFQAVAA4ABwAGAAgADgAOAAcAAwAEAAYACwAMAA4ADQAIAAAA+/8AAAYACwAKAAsACwAGAAEAAAACAAEAAAAAAP7//f/9//r/+v///wYADAALAAUABAABAP7//v8BAAUABgAHAAMA/f/7//z//v/9//7/AgADAAMABAABAAAAAQAAAAAA///9//z//v/+//r/+v/8//7//f/7//n/+P/1//T/+v8AAPr/+f/4//T/9P/+/wkABwD9//j/8f/r//f/BgAEAP7//P/0/+//+v8DAAAA9//x/+3/6v/p/+7/8//x/+f/4v/n/+7/8f/0//P/7f/t/+j/3P/f/+j/5v/j//H/AwAKAAwA///m/9P/zv/Z//b/FgAlABgA+v/Z/8j/1v/5/xEAEgACAOP/vP+m/7f/3f8AABAADAD//+z/2f/Q/87/0P/a/+j/8P/v/+v/6//r/+j/7v8AABEACQDg/7n/sP+8/8//6/8QACIAEQDw/+P/7P/5//3//v/1/9//0f/U/97/4f/f/9n/zf/F/8j/2//z/wIAAQD1/+v/5P/g/+L/5P/h/9f/0//R/9D/2P/l/+7/7//u/+j/3//b/9//7P/+/wUABgAHAAgABQAAAPv/6//V/8X/uv+4/8L/2P/q/+7/7P/p/+T/5f/n/+3/9//6//b/9f/1//P/7f/f/8v/wf/D/8n/zP/O/9D/0P/O/8//0f/T/93/6P/u/+//7//t/+b/2P/P/8n/x//L/9P/1//T/83/y//F/7v/u//D/8r/0v/h//L/+f/3//T/7f/h/9r/z//C/8L/zf/X/+T/8v/3/+v/3v/b/9P/zf/a/+7/9f/y/+7/6f/f/9f/1//X/9v/5P/v//v/AAACAAcABwACAPv/8//s/+//+P/7//3/AAABAAIABAAGAAIA+//1//X/9v/2//f///8FAAkADAAKAAEA+P/y//b/AQANABsAJAAeAAwAAAABABEAKAA4ADgALAAdAAwAAwAIABkAJwAlAB4AHAAdAB8AKAAqACEAEQADAAAAAQAVADQASQBOAEMALwAWAAQAAAAJABwANQBHAEYAOAAlABsAGwAbAB0AIAAjACgAKgAiABsAHAAjACoAMQA2AC0AFgAFAAMAEwAyAFMAZQBbAD0AGwD///z/EwAzAEkASwA+ACcAFwAWAB8AJwAwADwARgBMAE8ASQA8ACgAEwARAB8AMwBIAFUAUAA9ACYAGAAXACIANQA+AEAAOQApAB0AFwAYACAALAA4AD4AOwAvACYAIwAkAC0AOAA/ADgAKwAlACEAIwAsADYAPgA/ADYAJgAbABMADgAOABkAJAAnACoALAAkABcAEAAQABQAGAAZABgAFgAaAB8AHQAbAB4AHAAWABAADQATABoAHAAcABsAGwAdACEAHwAbABcAFgATAAsACgAMAAsADAAOABAAEQAQAA4ADgANAAkABgAKAA0ACwAHAAQAAAD//wEABwALAAwACQADAPz/+f/3//r/AQADAAIAAAD///r/8v/r/+n/6//w//T/9//7//3//v/+//r/9//5//z/+//8/////P/+//3//P/7//n/+v/8//3/+//4//X/9f/3//n/9//2//X/9P/1//b/8f/s/+3/7//y//j/+//8//j/9f/0//b/+P/7//3/+v/1//L/8v/x//H/8f/w/+//7//w//D/8//3//f/8//y//P/9f/0//X/9f/1//b/9f/0//b/+f/8///////8//n/9//4//n/+////wEAAQD///z/+v/3//X/9P/0//P/9P/3//X/8P/s/+v/6//u//D/8v/x/+//6//n/+3/8f/w/+//7P/q/+j/6P/o/+7/8f/2//f/8//w/+v/6P/o/+v/6P/r/+//7v/t/+7/7v/t/+7/6v/n/+b/5v/p/+v/6//v/+7/7f/s/+z/7P/s/+z/6//t//D/6//r/+3/7P/t//H/9f/0//H/7v/u/+7/7v/v/+//7//w//D/8v/2//f/9f/y//D/7f/r/+3/7//x//P/9v/5//j/9P/4//v//v/9//f/9v/4//T/8v/y/+7/7P/t//L/9//3//X/9v/5//X/8P/z//n/+f/4//b/+P/8//z/+//6//b/8v/0//j//P/9//j/9v/2//b/9v/6//z/+//6//v/+f/6//v//v///////P/8//r/9v/3//f/8v/z//P/9P/1//D/9f/2//X/9//4//X/8//3//7//v/8//z/+//6//n/+//6//j/9//2//j/+f/6//z/+P/2//b/+P/4//v/+f/2//b/9v/2//j/+//7//r//P/6//n/9f/2//b/8v/0//j//P8AAP///f/7//r/9//2//T/9v/3//b/9//7//z//f/+//z/+//+/wIAAwAAAPz/+v/4//f/+v///wEA///9//v//P/9//3///////7//P/+/wAAAAD///v/9//2//b/9P/z//L/8P/w//P/+f/5//r/+f/6//n/+f/6//v//P/+//7//P/8//3//f/6//v//P/9//7//v/7//n/+f/8//7//v/8//z//f/8//r/+f/2//b/9//4//j/9v/1//X/8//w//H/8//0//f/9//5//z//f/+//7//v/+//3//P/6//r/+f/6//j/9v/3//b/9//4//z//v8AAAIAAgADAAMAAwACAAEAAQAAAAAAAQABAP//+v/6//v//P8AAAMABwAFAAAA///+//v//f/+/wEABQAFAAcABQABAAAA/v/+/wAAAgAGAAgABgAEAAEAAAABAAQAAgABAAIAAAAAAAIAAgADAAUABAADAAMABgAIAAgACAAGAAcACAAKAAoADAAMAAsABwAFAAYACAAJAAsACwAJAAgABgAHAAgABwAIAAkACwAMAAsACAAFAAQABgAJAAsACwAKAAcABQACAAIAAwACAAQABwAJAA0ADgANAAsACwAJAAsADAAPABAAEQARABIAEgASABMADwANAAwACgAJAAcABwAHAAgACgALAAoACgAIAAkACwAKAAsACwAKAAsADQAPAA8ADQAMAAgABQAHAAcACQALAAsACwAKAAoACwAMAA0ADgAOAA4ADgAOAA0ACwAJAAgACAAJAAkACQAIAAUAAgACAAUACQAJAA0ADgANAAwADAAKAAoACgAIAAgACgANAA0ADgAOAA8ADAAJAAgABwAHAAcACwAPABAAEAANAAoACQAJAAoADAAMAA0ADAALAAgABwAGAAMABQAHAAcACAAMAAwACgAKAAoACAAKAAkACQALAAgACQAKAAcABwAHAAcAAwADAAUABQAGAAoACwALAAwADAANAAwADgAPABAAEAAQABAADgALAAkACAAGAAYABAACAAIAAwAFAAoACwAHAAgACAAHAAkACgANAA0ACwAMAAsACQAKAAoACQAIAAcACAAHAAUABwAHAAcABgAHAAkACwALAAsADAAMAAoACgAIAAcACgAMAAoACQAHAAYABAAEAAcABwAHAAgACAAIAAgACAAKAAsACgALAAgABgAGAAQABQAFAAIABAAEAAIABgAGAAUABAACAAEAAAABAAEAAgADAAIAAgABAAEAAQABAAAAAAAAAAAAAQACAAIAAgADAAIAAQAAAAAAAAD//////P/8//v/+//6//n/+//7//v//P/9//z//f/9//7/AAD//wAAAAD+//3//v/9//3//v/8//r/+P/3//j/+v/7//z//v/+//z//P/8//r//P/8//3//f/9//7//f/9//3//P/4//f/9//3//f/9v/0//P/8f/x//L/8f/0//f/+P/8//3/+//5//n/+f/6//3//f/+//3/+//6//j/9v/3//n/+P/6//r//f/8//z/+//7//r/+//+//3//v/9//z//P/8//z//v/+//3//P/7//b/9f/z/+//7P/s/+3/7//w//P/8//z//L/8//0//P/9v/3//b/9f/3//n/9v/5//f/9//3//b/9v/3//X/9P/0//P/9P/0//X/9P/0//T/9P/1//f/+P/7//z/+//8//r/+f/4//f/9//2//b/9//2//b/9v/1//P/8f/u//D/7//v//D/8f/x//L/8f/u/+//8P/y//L/9P/2//b/8//0//X/9f/2//b/8//x//H/8v/1//b/9v/3//X/8//x//H/8f/y//H/8f/x//L/9f/z//P/8//0//T/9v/3//f/+P/3//b/+P/5//j/+v/8//3//P/7//v//f/7//v//P/6//r//P/+////AAAAAAEAAgABAAAAAAAAAAAAAAAAAAAA///+//7//v///wAAAAAAAAEAAQAAAAAAAQABAAEAAgADAAEAAAAAAAAAAAABAAAAAAABAAIAAAAAAAAAAAAAAAEAAgACAAIAAgAAAP7//f/9//z//P/+//3///////7//v/+//3//v/9//7//v/+//3//v////7//v////7//v/+//3//P/8//v//P/9//7//v/9////AQAAAAAAAQABAAAA/////wAA///////////+////AAD+////AAAAAAAAAAADAAQABgAJAAoACgAJAAoACQAHAAkACQAIAAkACQAHAAQAAwABAAAAAAABAAMABQADAAQABAABAAAAAAABAAIAAwACAAMAAQAAAP7////9//z//P/9//z//f/8//v/+v/5//r/+f/8//z//f///wAA/f/+//7//f/7//7//f/9////AAAAAAAAAgABAAEAAQAAAAAAAQAAAAMABAAHAAcACAAKAAoACgAJAAkACwAMAA0ADwAQABIAEwAUABMAFAATABQAFQAWABYAFgAYABYAFAASABIAEwAUABYAFgAWABUAFQAUABYAFwAXABUAFQAUABMAEwATABQAFwAYABcAGQAZABgAGAAXABcAGAAYABgAFwAWABYAFAARABEAEQASABUAFwAXABcAGAAXABYAFgAXABcAFgAXABcAFwATABEAEAAOAAwACgAHAAUABAADAAMABAADAAMAAgACAAIAAgAFAAYABwAIAAoADQAQABQAGAAZAB0AHgAdABwAGwAbAB4AHgAeAB0AHQAaABgAGAAYABYAFQAUABMADwALAAkABwAFAAUABQAEAAQAAgAAAP/////9//3//f/8//7//f/+/wAAAQACAAQABAACAAMAAQAAAAEAAwAEAAUABAACAAMAAQABAAAA/v/9//j/9v/y//H/8P/t/+z/7P/s/+r/6P/p/+v/6//s/+//8P/w//L/9P/2//X/8v/0//P/8//1//f/+v/7//z//P/7//r/9//2//T/9P/z//D/7//s/+n/6P/l/+T/5f/l/+b/5//l/+T/5//o/+n/6v/t/+7/8P/v/+//8f/y//P/9v/2//f/+f/6//r/+//9//3//v8AAAAAAgAFAAcABwAKAAoACAAIAAkACQAIAAgACAAFAAYABAADAAQABAADAAAA/v/8//n/9f/z//D/7f/q/+v/6f/n/+T/5f/n/+j/6f/r/+7/8f/z//T/9//4//v//f/+//7///////7////////////+//3/+//9//z//f/8//v/+//3//T/8v/w//D/7P/q/+r/5//j/+H/4v/j/+P/4//j/+T/5v/p/+r/7P/s/+z/7//u/+3/7f/s/+z/7f/u/+//8v/z//T/9//6//z///8AAAIABAAEAAUABgAFAAQAAgD+//r/9f/x/+3/6f/l/+P/4v/f/9//4P/h/+T/5//t//H/8//3//v//f///wEAAAAAAAAA/f/6//n/9v/1//X/8//x//L/7//v//D/7v/t/+3/7f/v//D/8v/0//T/9f/4//j/9//4//r/+v/8//3///8AAAAA/v////z/+//8//3/+//7//3//v8AAP//AAD///7///8AAAAA//8AAP///f///wAAAAAAAAAAAwAGAAQABgAIAAgACAAJAAwADgAPABAAEQAUABMAFAAWABcAGQAaABsAHAAdABsAHAAbABoAGAAZABcAFQAUABEADwAOAAsACgAJAAgABwAGAAgABwAJAAsACwAPABIAFAAWABgAGQAZABoAHQAfAB8AHwAfAB4AHgAdABoAGAAXABgAFQAVABMAEwASABAAEAASABAAEAAQABAAEQAQABIAEgASABMAEQAOAA4ADQAMAAsADgAOAA4ADwAPAA4ADgALAAkABwAGAAUABAAEAAMAAQACAAMAAgACAAAAAAAAAAEAAgADAAYACAALAAsADQARABIAEwAUABQAFAAWABUAFQATABAAEAAOAA4ADQAKAAYAAwAAAP3/+//8//n/9v/2//f/9//1//X/9v/0//P/8v/w//H/8v/y//T/9v/3//r///8AAAQABgAJAAoACwALAAwADAAOAAwADAANAA4ADAANAA0ACgAIAAcABAAAAP//+v/5//b/9f/1//b/+P/5//r//P/8//3//P/8//z//f/9//7/AAABAAQABgAHAAkACgAGAAcACQAIAAcACAAJAAkACgALAAsADAANAAwADwAPAA8AEAAQABEADwAOAA4ACwAJAAkACQAJAAoACwAMAA0ADgAPABAAEAASABEADwARABEAEQAOAA0ADgANAAwADAANAA0ACwAMAAwACwAKAAsACwALAAwADQAPAA4ADAAJAAgABQADAAIAAwACAAIABQAGAAcACAAMAAwADQAOAA8ADgAOAAwACwANAAsACwAHAAMAAwABAP//AAACAAIAAwAFAAoACgANAA8ADQALAAwACgAIAAgABgAGAAUABgAEAAMAAwADAAMABAAFAAcACQAMAA8AEgAUABQAEgARABAADQAIAAUAAwABAP//+//9//3//P/7//z//v////////8AAAAA/v/+//3//f/9//3//P///wAAAAADAAcACQAMAA4ADgAQAA8ADAALAAkABQABAAAA/v/7//j/9v/0//P/8//0//P/8//z//X/9//3//n/+v/6//n/+v/5//n/+P/3//X/9f/0//T/8//1//T/9P/1//T/9v/3//f/9v/2//f/9v/2//X/9v/1//T/8//0//P/9P/0//T/9v/5//r/+v/7//v/+v/6//j/9f/w/+z/6f/l/9//2v/W/9X/1//X/9b/2f/b/9v/3f/i/+D/4f/l/+b/5v/m/+b/6f/q/+n/6f/p/+j/5f/m/+X/5P/k/+X/5//p/+3/7//v/+7/7v/w/+7/6//p/+j/5v/k/+L/4P/d/9v/3P/c/9r/3P/e/97/4P/k/+P/5P/l/+b/5v/l/+P/3//c/9j/1v/V/9P/0P/R/9P/0v/Q/9H/1f/X/9r/3//i/+X/6P/p/+n/6v/r/+z/6v/p/+j/5//n/+j/6f/o/+n/7P/u/+7/7P/s/+r/6P/m/+H/4P/b/9n/2f/Z/9n/3f/f/+D/4v/k/+f/5//o/+z/7P/t/+3/8P/x/+7/7v/v/+//7v/t/+r/6//r/+n/7v/x//L/9P/2//r/+//8//7//v/+//z/+f/3//P/9P/y/+//7v/x//P/9v/3//v///8DAAcABwAJAAsACgAJAAYABgACAAAA/f/5//b/9P/x/+7/7v/v/+7/7v/v//H/8v/0//b/+P/5//r/+f/5//j/+P/7//z//f///wAAAQADAAUACAAIAAkACgALAAwACgAJAAYAAgD////////8//3/AAD///3//v8AAP7//f/8//n/+f/2//X/9P/1//T/9P/0//P/9v/3//r//f8AAAEABAAFAAcACgAKAAgACgAHAAUABgAFAAIA///5//j/9//x/+//8P/w//L/9v/5//7///8DAAQABAAEAAUABgAGAAUABAADAAEA/v/9//v/+f/6//r/+//3//f/+P/4//b/9//3//n/+v/7//3/AAAAAAQABwAIAAcACQAHAAcACAAKAAsACwAPABMAEwAVABcAFwAWABUAEgAPAA8ADQAMAAoACgAGAAcABwAFAAcACgALAA4AEQATABUAFgAWABcAGAAZABsAHgAeAB8AIgAgACAAIQAhACAAHwAfAB8AIAAgACAAHwAcABsAGwAXABUAEwATABIAEAAQABMAFQAVABUAFQAWABcAFwAYABwAHAAbAB4AIQAiACMAJQAmACUAKAAmACMAJAAhACAAIAAfAB4AHQAdABwAGgAZABcAFgATABIAEwATABUAGAAaABwAHQAhACMAIQAhACIAIgAjACMAJAAmACYAJAAjACMAJAAjACQAJAAlACYAJQAkACQAIwAhACMAIgAgACAAHwAdAB8AHgAaABkAFgAVABMAEQAQAA4ADAALAA0ADwAPABEAEwAWABQAFwAWABUAFgAZABkAHAAdABwAHwAgACAAIgAjACAAHwAfACAAHQAaABkAFAAQAA4ACwAKAAkACgAKAAoADQANAAwADQAMAAsACQAIAAcACAAIAAkACwAMAA4ADQAMAAkABwAFAAUABAAFAAUABQAEAAQABQAGAAgACAALAA4ADAAMAA8ADwAKAAoACQAJAAcABgAHAAkACwAMAA0ADgANAAwADAAMAAsACgAIAAYABQAEAA==",
                    )
                ]
            )
        )
        self._send_client_event(ce)

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
        self.logger.debug("send client event type %s, data is %r", type(event), data)
        self.connection.send(data)

    def respond_error_message(self, error: str) -> None:
        self.server_ctx.respond_error_message(error)
