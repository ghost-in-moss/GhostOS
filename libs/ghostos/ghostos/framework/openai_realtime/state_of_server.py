from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Protocol, Optional, Dict, List, Union
from typing_extensions import Self
from ghostos.framework.openai_realtime.event_from_server import *
from ghostos.framework.openai_realtime.event_data_objects import (
    MessageItem,
    RateLimit,
    SessionObject,
)
from pydantic import ValidationError
from ghostos.core.messages import Message, MessageType
from ghostos.contracts.logger import LoggerItf
from ghostos_container import get_caller_info


class ServerContext(Protocol):
    logger: LoggerItf

    @abstractmethod
    def respond_message_chunk(self, response_id: str, chunk: Union[Message, None]) -> bool:
        """
        respond a message chunk usually a text chunk.
        :param response_id:
        :param chunk:
        :return:
        """
        pass

    @abstractmethod
    def respond_error_message(self, error: str) -> None:
        """
        output error message
        :param error:
        :return:
        """
        pass

    @abstractmethod
    def update_history_message(self, message: Message) -> None:
        """
        update history message
        :param message:
        :return:
        """
        pass

    @abstractmethod
    def update_local_conversation(self) -> None:
        """
        update realtime conversation with local conversation
        """
        pass

    @abstractmethod
    def add_message_item(self, item: MessageItem, previous_item_id: Optional[str] = None) -> None:
        """
        add realtime message item to update history message
        :param item:
        :param previous_item_id:
        :return:
        """
        pass

    @abstractmethod
    def respond_audio_chunk(self, response_id: str, item_id: str, data: bytes) -> bool:
        """
        respond
        :param response_id:
        :param item_id:
        :param data:
        :return:
        """
        pass

    @abstractmethod
    def save_audio_item(self, item: MessageItem) -> None:
        """
        save audio data to local storage
        :param item:
        :return:
        """
        pass

    @abstractmethod
    def start_server_response(self, response_id: str) -> None:
        """
        start server response
        :param response_id:
        :return:
        """
        pass

    @abstractmethod
    def get_server_response_id(self) -> Optional[str]:
        pass

    @abstractmethod
    def end_server_response(self, response_id: str) -> bool:
        """
        end but not cancel a response.
        :param response_id:
        :return:
        """
        pass

    @abstractmethod
    def clear_client_audio_buffer(self) -> None:
        pass

    @abstractmethod
    def set_client_audio_buffer_start(self, cut_ms: int) -> None:
        pass

    @abstractmethod
    def set_client_audio_buffer_stop(self, item_id: str, end_ms: int) -> None:
        pass


class StateOfServer(ABC):

    def __init__(self, ctx: ServerContext):
        self.ctx = ctx
        self._destroyed = False

    @classmethod
    def recv_event(cls, state: Self, event: dict) -> None:
        try:
            state.receive(event)
        except ValidationError as e:
            state.ctx.logger.error("unwrap event failed: %r, origin event: %r", e, event)
            raise e

    @abstractmethod
    def recv(self, event: dict) -> None:
        """
        recv an openai realtime server event, and handle it.
        recv one server event at a time globally.
        :param event:
        :return:
        """
        pass

    def __del__(self):
        self.destroy()

    def destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        self._destroy()

    @abstractmethod
    def _destroy(self):
        pass

    def recv_invalid_event(self, event: dict):
        type_ = ServerEventType.get_type(event)
        if ServerEventType.error.value == type_:
            se = ServerError(**event)
            # send error message.
            self.ctx.logger.error("state %s recv server error: %r", type(self), se.error)
            return self.ctx.respond_error_message(se.error.message)
        else:
            self.ctx.logger.error("state %s receive invalid event: %s", type(self), str(event)[:100])

    def ack_server_event(self, event: ServerEvent):
        line = get_caller_info(2, with_full_file=False)
        self.ctx.logger.debug(
            "ack event: event `%s`  id `%s' by state %s at line `%s`",
            event.type, event.event_id, type(self), line,
        )


class SessionState(StateOfServer):
    """
    session is the root of server state
    """

    def __init__(
            self,
            ctx: ServerContext,
            session_created: ServerSessionCreated,
    ):
        super().__init__(ctx)
        self.conversation = ConversationState(ctx, session_id="", conversation_id="")
        self.session_id = session_created.session.id
        self.session_obj: SessionObject = session_created.session
        self.input_audio = InputAudioState(ctx)
        self.tokens_rate_limit: Optional[RateLimit] = None
        self.requests_rate_limit: Optional[RateLimit] = None

    def is_responding(self) -> bool:
        return self.conversation.responding_id is not None

    def recv(self, event: dict):
        type_name = ServerEventType.get_type(event)
        if ServerEventType.error.value == type_name:
            return self.recv_invalid_event(event)
        elif ServerEventType.is_session_event(event, type_name):
            return self._recv_session_event(event, type_name)

        elif ServerEventType.rate_limits_updated.value == type_name:
            return self._update_rate_limit(event)

        # input audio event
        elif ServerEventType.is_input_audio_event(event, type_name):
            return self._recv_input_audio_event(event)

        # conversation event
        elif ServerEventType.is_conversation_event(event, type_name):
            return self._recv_conversation_event(event)

        # response event
        elif ServerEventType.is_respond_event(event, type_name):
            return self._recv_response_event(event)
        else:
            return self.recv_invalid_event(event)

    def _destroy(self):
        self.conversation.destroy()
        self.input_audio.destroy()
        del self.conversation
        del self.input_audio
        del self.session_obj
        del self.ctx

    def _recv_session_event(self, event: dict, e_type: str):
        if e_type == ServerSessionCreated.type:
            obj = ServerSessionCreated(**event)
            self.session_id = obj.session.id
            self.session_obj = obj.session

        elif e_type == ServerSessionUpdated.type:
            obj = ServerSessionUpdated(**event)
            if self.session_id and obj.session.id != self.session_id:
                # recv other session event, which is not possible.
                return self.recv_invalid_event(event)
            self.ctx.logger.info("realtime session updated: %r", obj.session)
            self.session_obj = obj.session
        else:
            return self.recv_invalid_event(event)

    def _recv_response_event(self, event: dict):
        # let conversation handle response event
        return self.conversation.recv(event)

    def _recv_conversation_event(self, event: dict):
        return self.conversation.recv(event)

    def _recv_input_audio_event(self, event: dict):
        return self.input_audio.recv(event)

    def _update_rate_limit(self, event: dict):
        # todo: use rate limit in future.
        rlu = RateLimitsUpdated(**event)
        for limit in rlu.rate_limits:
            if limit.name == "requests":
                self.requests_rate_limit = limit
            elif limit.name == "tokens":
                self.tokens_rate_limit = limit
        self.ctx.logger.info(f"Rate limit updated {rlu}")
        self.ack_server_event(rlu)


class ConversationState(StateOfServer):

    def __init__(
            self,
            ctx: ServerContext,
            session_id: str,
            conversation_id: str,
    ):
        super().__init__(ctx)
        self.session_id = session_id
        self.conversation_id = conversation_id
        # session-conversation completed item.
        self.conversation_item_states: dict[str, ConversationItemState] = {}
        self.responses: Dict[str, ResponseState] = {}
        self.responding_id: Optional[str] = None

    def _destroy(self):
        for item in self.conversation_item_states.values():
            item.destroy()
        self.conversation_item_states = {}
        for item in self.responses.values():
            item.destroy()
        self.responses = {}
        self.responding_id = None

    def get_conversation_items(self) -> List[ConversationItemState]:
        """
        return the conversation items in orders.
        """
        items = []
        start_item_id = ""
        item_ids = set()
        next_item_trace = {}
        for key, item in self.conversation_item_states.items():
            item_ids.add(key)
            if not item.previous_item_id:
                start_item_id = key
            else:
                next_item_trace[item.previous_item_id] = key
        if not start_item_id:
            for item_id in item_ids:
                if item_id not in next_item_trace:
                    start_item_id = item_id
                    break

        current_item_id = start_item_id
        while current_item_id in self.conversation_item_states:
            item = self.conversation_item_states[current_item_id]
            items.append(item)
            current_item_id = next_item_trace[current_item_id]
        return items

    def recv(self, event: dict):
        type_name = ServerEventType.get_type(event)
        # conversation events
        if ServerEventType.conversation_created.match(event):
            return self._conversation_created(event)
        elif ServerEventType.conversation_item_created.value == type_name:
            return self._conversation_item_created(event)
        elif ServerEventType.conversation_item_deleted.value == type_name:
            return self._delete_item(event)

        # item event
        elif ServerEventType.conversation_item_truncated.value == type_name:
            return self._send_event_to_item(event)
        elif ServerEventType.conversation_item_input_audio_transcription_completed.value == type_name:
            return self._send_event_to_item(event)
        elif ServerEventType.conversation_item_input_audio_transcription_failed.value == type_name:
            return self._send_event_to_item(event)

        # response event
        elif ServerEventType.is_respond_event(event):
            return self._on_response_event(event)
        else:
            return self.recv_invalid_event(event)

    def _conversation_created(self, event: dict):
        cic = ConversationItemCreated(**event)
        self.conversation_id = cic.conversation_id
        return self.ack_server_event(cic)

    def _conversation_item_created(self, event: dict):
        server_event = ConversationItemCreated(**event)
        item = server_event.item
        if item.id not in self.conversation_item_states:
            conversation_item_state = ConversationItemState(
                ctx=self.ctx,
                created_event=server_event,
            )
            self.conversation_item_states[item.id] = conversation_item_state
            if len(self.conversation_item_states) > 4:
                first = list(self.conversation_item_states.keys())[0]
                if first != item.id:
                    del self.conversation_item_states[first]
        else:
            # let conversation_item_state handle the item event.
            state = self.conversation_item_states[item.id]
            return state.recv(event)

    def _delete_item(self, event: dict):
        cid = ConversationItemDeleted(**event)
        item_id = cid.item_id
        # delete exists conversation item.
        if item_id in self.conversation_item_states:
            del self.conversation_item_states[item_id]
            self.ctx.logger.info(f"Deleted item {item_id}")
            return self.ack_server_event(cid)
        return self.recv_invalid_event(event)

    def _on_response_event(self, event: dict):
        response_id = ServerEventType.get_response_id(event)
        if not response_id:
            # response_id exists in protocol
            return self.recv_invalid_event(event)

        if response_id not in self.responses:
            if not ServerEventType.response_created.match(event):
                self.ctx.logger.error("Response is not created")
            else:
                rc = ResponseCreated(**event)
                response = self._create_response(rc)
                self.responses[response.response_id] = response
                return None
        # response exists.
        response = self.responses[response_id]
        response.recv(event)
        if response.is_done():
            # if response is done, reset current responding id.
            self.responding_id = None

    def _send_event_to_item(self, event: dict):
        item_id = ServerEventType.get_item_id(event)
        # todo:
        if item_id in self.conversation_item_states:
            return self.conversation_item_states[item_id].recv(event)
        return self.recv_invalid_event(event)

    def _create_response(self, event: ResponseCreated) -> ResponseState:
        # return response state
        return ResponseState(
            ctx=self.ctx,
            event=event,
        )


class ConversationItemState(StateOfServer):
    def __init__(
            self,
            ctx: ServerContext,
            created_event: ConversationItemCreated,
    ):
        super().__init__(ctx)
        self.previous_item_id: Optional[str] = created_event.previous_item_id
        self.item: MessageItem = created_event.item
        self.message = created_event.item.to_message_head().as_tail(copy=True)
        self._on_conversation_item_created(created_event)

    def _destroy(self):
        self.item = None

    def recv(self, event: dict):
        type_name = ServerEventType.get_type(event)

        # conversation item is created yet.
        if ServerEventType.conversation_item_created.value == type_name:
            obj = ConversationItemCreated(**event)
            return self._on_conversation_item_created(obj)

        elif ServerEventType.conversation_item_truncated.value == type_name:
            obj = ConversationItemTruncated(**event)
            # todo truncate audio file
            return self.ack_server_event(obj)

        elif ServerEventType.conversation_item_input_audio_transcription_completed.value == type_name:
            obj = ConversationInputAudioTranscriptionCompleted(**event)
            # update transcription.
            self.message.content = obj.transcript
            self.message.type = MessageType.AUDIO.value
            self.ctx.update_history_message(self.message)
            return self.ack_server_event(obj)

        elif ServerEventType.conversation_item_input_audio_transcription_failed.value == type_name:
            obj = ConversationInputAudioTranscriptionFailed(**event)
            # todo
            self.ctx.logger.error(f"Conversation item {self.item.id} transcription failed: %r", obj.error)
            return self.ack_server_event(obj)
        else:
            return self.recv_invalid_event(event)

    def _on_conversation_item_created(self, server_event: ConversationItemCreated):
        self.previous_item_id = server_event.previous_item_id
        self.item = server_event.item
        self.message = self.item.to_message_head().as_tail(copy=True)
        # add new message item.
        self.ctx.add_message_item(server_event.item, server_event.previous_item_id)
        if self.item is None:
            self.ctx.logger.info("receive conversation item created but is None: %r", server_event)
        if self.item and self.item.has_audio():
            # save audio.
            self.ctx.save_audio_item(self.item)
        return self.ack_server_event(server_event)


class InputAudioState(StateOfServer):

    def recv(self, event: dict):
        type_name = ServerEventType.get_type(event)
        if ServerEventType.input_audio_buffer_cleared == type_name:
            return self._on_input_audio_buffer_cleared(event)
        elif ServerEventType.input_audio_buffer_committed == type_name:
            return self._on_input_audio_buffer_committed(event)
        elif ServerEventType.input_audio_buffer_speech_started == type_name:
            return self._on_input_audio_buffer_started(event)
        elif ServerEventType.input_audio_buffer_speech_stopped == type_name:
            return self._on_input_audio_buffer_stopped(event)

    def _on_input_audio_buffer_stopped(self, event: dict):
        se = InputAudioBufferSpeechStopped(**event)
        self.ctx.set_client_audio_buffer_stop(se.item_id, se.audio_end_ms)
        return self.ack_server_event(se)

    def _on_input_audio_buffer_started(self, event: dict):
        """
        the input audio started.
        :param event
        :return:
        """
        se = InputAudioBufferSpeechStarted(**event)
        self.ctx.set_client_audio_buffer_start(se.audio_start_ms)
        return self.ack_server_event(se)

    def _on_input_audio_buffer_committed(self, event: dict):
        se = InputAudioBufferCommitted(**event)
        # todo:
        return self.ack_server_event(se)

    def _on_input_audio_buffer_cleared(self, event: dict):
        se = InputAudioBufferCleared(**event)
        return self.ack_server_event(se)

    def _destroy(self):
        pass


class ResponseState(StateOfServer):
    """
    handle all response events.
    """

    def __init__(
            self,
            ctx: ServerContext,
            event: ResponseCreated,
    ):
        super().__init__(ctx)
        self.response_id = event.response.id
        self.response_obj = event.response
        self.item_states: dict[str, ResponseItemState] = {}
        self.responding_item_id: Optional[str] = None
        self._on_response_created(event)

    def _destroy(self):
        for item in self.item_states.values():
            item.destroy()
        self.item_states = {}

    def is_done(self) -> bool:
        return self.response_obj.status in {"completed", "cancelled", "failed"}

    def recv(self, event: dict) -> None:
        type_name = ServerEventType.get_type(event)
        response_id = ServerEventType.get_response_id(event)
        # receive current response event only
        if response_id != self.response_id:
            return self.recv_invalid_event(event)

        if ServerEventType.response_created.value == type_name:
            rc = ResponseCreated(**event)
            return self.ack_server_event(rc)

        elif ServerEventType.response_done.value == type_name:
            return self._on_response_done(event)

        elif ServerEventType.response_output_item_added.value == type_name:
            # send head package
            return self._on_response_output_item_added(event)

        elif self.responding_item_id:
            item_state = self.item_states[self.responding_item_id]
            # let the item state handle event
            item_state.recv(event)
            # update the status after item is added
            if item_state.is_done():
                self.responding_item_id = None

        else:
            return self.recv_invalid_event(event)

    def _on_response_created(self, event: ResponseCreated):
        self.response_obj = event.response
        self.response_id = event.response.id

        # start response
        self.ctx.start_server_response(self.response_id)
        return self.ack_server_event(event)

    def _on_response_done(self, event: dict) -> None:
        """
        response is done, update the
        """
        rd = ResponseDone(**event)
        # update message item
        self.response_obj = rd.response
        self.ctx.end_server_response(rd.response.id)
        if rd.response.status not in ["completed", "cancelled"] and rd.response.status_details:
            error = rd.response.status_details.error
            if error:
                self.ctx.logger.error("response done with error: %s", error)
                self.ctx.respond_error_message(repr(error))

        elif rd.response.output:
            # update history messages again
            for item in rd.response.output:
                self.ctx.update_history_message(item.to_complete_message())
        # update local conversation when response is done.
        self.ctx.update_local_conversation()
        return self.ack_server_event(rd)

    def _on_response_output_item_added(self, event: dict) -> None:
        se = ResponseOutputItemAdded(**event)
        item_id = se.item.id
        if not item_id:
            return self.recv_invalid_event(event)
        # create response item state
        state = ResponseItemState(self.ctx, se)
        self.item_states[item_id] = state
        self.responding_item_id = item_id


class ResponseItemState(StateOfServer):

    def __init__(self, ctx: ServerContext, event: ResponseOutputItemAdded):
        super().__init__(ctx)
        self.item = event.item
        self.response_id = event.response_id
        self.output_index = event.output_index
        # send head
        self._on_response_output_item_added(event)

    def _destroy(self):
        pass

    def is_done(self) -> bool:
        return self.item.status in {"completed"}

    def _on_response_output_item_added(self, event: ResponseOutputItemAdded):
        self.ctx.respond_message_chunk(event.response_id, event.item.to_message_head())
        return self.ack_server_event(event)

    def recv(self, event: dict) -> None:
        type_name = ServerEventType.get_type(event)
        if ServerEventType.response_output_item_added.value == type_name:
            se = ResponseOutputItemAdded(**event)
            return self._on_response_output_item_added(se)

        elif ServerEventType.response_output_item_done.value == type_name:
            # update message item.
            se = ResponseOutputItemDone(**event)
            return self._on_response_output_item_done(se)

        elif ServerEventType.response_content_part_added.value == type_name:
            se = ResponseContentPartAdded(**event)
            return self._on_response_content_part_added(se)

        elif ServerEventType.response_content_part_done.value == type_name:
            se = ResponseContentPartDone(**event)
            return self._on_response_content_part_done(se)

        elif ServerEventType.response_text_delta.value == type_name:
            se = ResponseTextDelta(**event)
            self.ctx.respond_message_chunk(se.response_id, se.as_message_chunk())
            return self.ack_server_event(se)

        elif ServerEventType.response_text_done.value == type_name:
            se = ResponseTextDone(**event)
            return self.ack_server_event(se)

        elif ServerEventType.response_audio_delta.value == type_name:
            se = ResponseAudioDelta(**event)
            self.ctx.respond_audio_chunk(se.response_id, se.item_id, se.get_audio_bytes())
            return self.ack_server_event(se)

        elif ServerEventType.response_audio_done.value == type_name:
            se = ResponseAudioDone(**event)
            return self.ack_server_event(se)

        elif ServerEventType.response_audio_transcript_delta.value == type_name:
            se = ResponseAudioTranscriptDelta(**event)
            self.ctx.respond_message_chunk(se.response_id, se.as_message_chunk())
            return self.ack_server_event(se)

        elif ServerEventType.response_audio_transcript_done.value == type_name:
            se = ResponseAudioTranscriptDone(**event)
            return self.ack_server_event(se)

        elif ServerEventType.response_function_call_arguments_delta.value == type_name:
            se = ResponseFunctionCallArgumentsDelta(**event)
            self.ctx.respond_message_chunk(se.response_id, se.as_message_chunk())
            return self.ack_server_event(se)

        elif ServerEventType.response_function_call_arguments_done.value == type_name:
            se = ResponseFunctionCallArgumentsDone(**event)
            chunk = se.as_message()
            self.ctx.respond_message_chunk(se.response_id, chunk)
            self.ctx.logger.info("receive function call done: %s", repr(se))

            return self.ack_server_event(se)

        else:
            return self.recv_invalid_event(event)

    def _on_response_output_item_done(self, event: ResponseOutputItemDone) -> None:
        self.item = event.item
        done = event.item.to_complete_message()
        self.ctx.logger.info("response done with event: %s, message is %s", repr(event), repr(done))
        self.ctx.update_history_message(done)
        return self.ack_server_event(event)

    def _on_response_content_part_added(self, event: ResponseContentPartAdded) -> None:
        return self.ack_server_event(event)

    def _on_response_content_part_done(self, event: ResponseContentPartDone) -> None:
        return self.ack_server_event(event)
