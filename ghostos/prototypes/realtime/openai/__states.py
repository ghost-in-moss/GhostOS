from __future__ import annotations
from abc import abstractmethod, ABC
from typing import (
    Self, Literal, List, Optional, Union, Dict, Protocol, ClassVar, Type, Callable, Tuple,
    Iterable,
)
from enum import Enum
from ghostos.prototypes.realtime.abcd import (
    ConversationProtocol,
    State,
    OperationType, RealtimeOperator,
)
from ghostos.helpers import uuid
from ghostos.abcd import Conversation
from ghostos.contracts.logger import LoggerItf, get_logger
from ghostos.core.messages import Message, MessageType
from ghostos.container import Container
from pydantic import BaseModel, Field
from collections import deque
from .event_from_server import *
from .ws import OpenAIWebsocketsConf, OpenAIWSConnection
from .configs import OpenAIRealtimeConf
from .broadcast import SimpleBroadcaster, Broadcaster
from .utils import parse_message_to_client_event, parse_server_event_to_message


class StateCtx:

    def __init__(
            self,
            conf: OpenAIRealtimeConf,
            container: Container,
            conversation: Conversation,
            logger: LoggerItf,
            connection: Optional[OpenAIWSConnection],
    ):
        self.conf: OpenAIRealtimeConf = conf
        self.container = container
        self.logger: LoggerItf = logger
        self.conversation: Conversation = conversation
        self.connection: Optional[OpenAIWSConnection] = connection

    def recv_from_server_nowait(self) -> Union[dict, None]:
        if self.connection is None:
            return None
        return self.connection.recv(timeout=0)

    def publish_event(self, event: Union[dict, None]):
        type_ = ServerEventType.get_type(event)
        self.broadcaster.publish(type_, event)

    def send_to_server(self, event: ClientEvent):
        if not self.connection:
            raise RuntimeError("No connection to send event")
        self.connection.send(event.to_openai_event())

    def messages(self) -> List[Message]:
        raise NotImplementedError("todo")


class AbsState(State, ABC):
    """
    base state class
    """

    prior_ops: ClassVar[Set[OperatorType]]
    pending_ops: ClassVar[Set[OperatorType]]
    block_ops: ClassVar[Dict[str, OperatorType]]

    include_events: ClassVar[Union[Set[ServerEventType], None]] = None
    exclude_events: ClassVar[Union[Set[ServerEventType], None]] = None

    def __init__(
            self,
            ctx: StateCtx,
    ):
        self._ctx = ctx
        self._op_queue = deque()
        self._inited = False

    @abstractmethod
    def _on_state_created(self) -> None:
        pass

    def _run_operator(self, op: AbsOperator) -> State:
        return op.run(self._ctx)

    def conversation(self) -> ConversationProtocol:
        return self._ctx.conversation

    def operate(self, op: AbsOperator) -> Tuple[OperationType, Union[str, None]]:
        if not self._inited:
            self._on_state_created()

        type_ = op.type
        if type_ in self.block_ops:
            return "blocked", self.block_ops[type_]
        elif type_ in self.prior_ops:
            self._op_queue.insert(0, op)
            return "", None
        elif type_ in self.pending_ops:
            self._op_queue.append(op)
            return "queued", None
        else:
            return "illegal", "operation not allowed"

    def run_operator(self) -> Union[State, None]:
        if not self._inited:
            self._inited = True
            # block when ticked.
            self._on_state_created()
        if len(self._op_queue) == 0:
            return None
        op = self._op_queue.popleft()
        return self._run_operator(op)

    def run_frame(self) -> Union[State, None]:
        e = self._ctx.recv_from_server_nowait()
        if e is None:
            return None

        # ignore event
        e = self._filter_server_event(e)
        if e is None:
            return None

        # broadcast first.
        self._ctx.publish_event(e)
        # add conversation item
        self._filter_conversation_message(e)

        # handle server event that should add message to conversation.
        return self._handle_server_event(e)

    def _filter_server_event(self, e: dict) -> Union[dict, None]:
        # ignore checks
        type_ = ServerEventType.get_type(e)
        if self.include_events and type_ not in self.include_events:
            # ignore
            return None
        if self.exclude_events and type_ in self.exclude_events:
            return None
        return e

    def _filter_conversation_message(self, e: dict) -> None:
        # add conversation item.
        message = parse_server_event_to_message(e)
        if message is not None:
            self._ctx.conversation.add(message)

    def _handle_server_event(self, event: dict) -> Union[State, None]:
        # handle later
        type_ = ServerEventType.get_type(event)
        method = f"_on_{type_.name}"
        if hasattr(self, method):
            _new_state = getattr(self, method)(event)
            if _new_state:
                return _new_state
        # default is ignore
        return None

    def _on_response_created(self, event: dict) -> Union[State, None]:
        return RespondingState(self._ctx)

    def join(self):
        del self._ctx


class ConnectingState(AbsState):
    """
    create websocket connection
    """
    state_name = StateName.connecting

    prior_ops = {
        OperatorName.stop,
        OperatorName.session_update,
    }
    block_ops = {
        OperatorName.reconnect,
    }
    include_events = {
        ServerEventType.session_created,
    }

    def _on_state_created(self):
        if self._ctx.connection is not None:
            # close the old one
            self._ctx.connection.close()
            self._ctx.connection = None

        socket = None
        if self._ctx.connect_sock:
            socket = self._ctx.connect_sock()
        # always connect at first.
        self._connection = OpenAIWSConnection(
            self._ctx.conf.ws_conf,
            sock=socket,
            logger=self._ctx.logger,
        )

    def _on_session_created(self, event: dict) -> Union[State, None]:
        e = ServerSessionCreated(**event)

        # align the session
        session_obj = self._ctx.get_session_obj()
        # shall update session
        if session_obj:
            # update session
            send = ClientSessionUpdateEvent(session=session_obj)
            self._ctx.send_to_server(send)
            # update conversation
            messages = self._ctx.messages()
            for item in messages:
                e = parse_message_to_client_event(item)
                if e is not None:
                    self._ctx.send_to_server(e)

            # new state.
            return SessionUpdatingState(self._ctx)
        else:
            # use default session.
            self._ctx.session = e.session
            return IdleState(self._ctx)


class SessionUpdatingState(AbsState):
    """
    updating session.
    """
    state_name = StateName.session_updating

    prior_ops = {
        OperatorName.stop,
        OperatorName.reconnect,

    }
    pending_ops = {
        OperatorName.create_response,
        OperatorName.text_input,
        OperatorName.function_output,
        OperatorName.input_audio,
        OperatorName.start_listening,
    }
    block_ops = {
        OperatorName.response_cancel: "not responding",
        OperatorName.truncate_listening: "not listening",
        OperatorName.session_update: "updating session",
    }

    def _on_state_created(self) -> None:
        session = self._ctx.get_session_obj()
        update = ClientSessionUpdateEvent(session=session)
        self._ctx.send_to_server(update)


class IdleState(AbsState):
    state_name = StateName.idle

    prior_ops = {
        OperatorName.stop,
        OperatorName.reconnect,
        OperatorName.response_cancel,
        OperatorName.input_audio,
        OperatorName.start_listening,
    }
    pending_ops = {
        OperatorName.create_response,
        OperatorName.session_update,
        OperatorName.text_input,
        OperatorName.function_output,
    }
    block_ops = {
        OperatorName.truncate_listening: "not listening",
    }

    def _on_state_created(self) -> None:
        return None


class RespondingState(AbsState):
    state_name = StateName.responding

    prior_ops = {
        OperatorName.stop,
        OperatorName.reconnect,
        OperatorName.response_cancel,
        OperatorName.input_audio,
        OperatorName.start_listening,
    }
    pending_ops = {
        OperatorName.session_update,
        OperatorName.text_input,
        OperatorName.function_output,
    }
    block_ops = {
        OperatorName.create_response: "responding",
        OperatorName.truncate_listening: "not listening",
    }

    def __init__(self, ctx: StateCtx, response_id: str):
        super().__init__(ctx)
        self._response_id = response_id

    def _on_state_created(self):
        return


class StoppedState(AbsState):
    state_name = StateName.stopped
    prior_ops = {}
    pending_ops = {}
    block_ops = {
        OperatorName.stop: "is stopped"
    }

    def _on_state_created(self) -> None:
        return None

    def join(self):
        if self._ctx.connection is not None:
            self._ctx.connection.close()


class ListeningState(AbsState):
    prior_ops = {
        OperatorName.stop,
        OperatorName.reconnect,
        OperatorName.create_response,
        OperatorName.truncate_listening,
        OperatorName.function_output,
    }
    pending_ops = {
        OperatorName.session_update,
        OperatorName.text_input,
    }
    block_ops = {
        OperatorName.input_audio: "is listening",
        OperatorName.response_cancel: "listening",
        OperatorName.start_listening: "is listening",
    }

    def _on_state_created(self) -> None:
        pass


class FailedState(AbsState):
    prior_ops = {
        OperatorName.stop,
        OperatorName.reconnect,
    }
    pending_ops = set()
    block_ops = {
        OperatorName.response_cancel: "failed, reconnect or stop",
        OperatorName.input_audio: "failed, reconnect or stop",
        OperatorName.start_listening: "failed, reconnect or stop",
        OperatorName.session_update: "failed, reconnect or stop",
        OperatorName.text_input: "failed, reconnect or stop",
        OperatorName.function_output: "failed, reconnect or stop",
        OperatorName.create_response: "failed, reconnect or stop",
        OperatorName.truncate_listening: "failed, reconnect or stop",
    }
    include_events = {
        ServerEventType.error,
    }

    def _on_state_created(self) -> None:
        if self._ctx.connection is not None:
            self._ctx.connection.close()


# --- operators --- #

class OperatorType(str, Enum):
    stop = "stop"
    reconnect = "reconnect"
    function_output = "function_output"
    update_session = "update_session"


class AbsOperator(RealtimeOperator):

    def on_accept(self, ctx: StateCtx):
        return

    @abstractmethod
    def run(self, ctx: StateCtx) -> Union[State, None]:
        """
        default action of the operator.
        """
        pass


class Stop(AbsOperator):
    type = OperatorType.stop

    def run(self, ctx: StateCtx) -> Union[State, None]:
        return StoppedState(ctx)


class Reconnect(AbsOperator):
    type = OperatorType.reconnect

    def run(self, ctx: StateCtx) -> Union[State, None]:
        return ConnectingState(ctx)


class FunctionOutput(AbsOperator):
    type = OperatorType.function_output
    call_id: str
    output: str

    def on_accept(self, ctx: StateCtx):
        # message = MessageType.FUNCTION_OUTPUT.new(
        #     role="",
        # )
        pass

    def run(self, ctx: StateCtx) -> Union[State, None]:
        pass


class UpdateSession(RealtimeOperator):
    type = OperatorType.update_session

    instruction: Optional[str] = Field(
        default=None,
        description="Instruction of the session",
    )
    tool_choice: str = Field(default="auto")
    tools: List[Function] = Field(default_factory=list)
