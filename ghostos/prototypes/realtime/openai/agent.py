from __future__ import annotations
import time
from typing import List, Optional, Dict, Iterable, Tuple, Callable, Union
from threading import Thread
from ghostos.prototypes.realtime.abcd import (
    Function, RealtimeAgent,
    Shell,
    Ghost, Message,
    Operator, OperationType, ChanIn,
    ConversationProtocol,
)
from ghostos.container import Container
from ghostos.contracts.logger import LoggerItf, get_logger
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from .protocols import StateName, ServerEventType
from .configs import AgentConf
from .states import AbsState, ConnectingState, StateCtx
from .broadcast import SimpleBroadcaster, Broadcaster


class Agent(RealtimeAgent):

    def __init__(
            self,
            conf: AgentConf,
            container: Container,
            conversation: ConversationProtocol,
            proxy: Optional[Callable] = None,
    ):
        self._container = Container(parent=container)
        self._conf = conf
        self._conversation = conversation
        self._state: AbsState | None = None
        self._container.set(RealtimeAgent, self)
        self._container.set(ConversationProtocol, self._conversation)
        self._proxy = proxy
        self._logger = container.get(LoggerItf)
        self._pool = ThreadPoolExecutor(max_workers=2)
        if self._logger is None:
            self._logger = get_logger()

        self._closed: bool = False
        self._started = False

    def run_util_stop(self, *shells: Shell) -> None:
        if self._started:
            raise RuntimeError("agent already started")

        _funcs: Dict[str, List[Function]] = {}
        _broadcast: Broadcaster = SimpleBroadcaster()
        # bind shells.
        for shell in shells:
            self._add_shell(shell, _broadcast, _funcs)

        _ctx = StateCtx(
            conf=self._conf,
            container=self._container,
            funcs=_funcs,
            conversation=self._conversation,
            broadcaster=_broadcast,
            session=None,
            connection=None,
            connect_sock=self._proxy,
            logger=self._logger,
        )

        self._state = ConnectingState(_ctx)
        while not self._closed:
            state = self._state
            new_state = state.tick()
            if new_state is None:
                time.sleep(0.05)
            else:
                # destroy
                self._pool.submit(state.join)
                # renew the state
                self._state = new_state
                if new_state.state_name == StateName.stopped:
                    # stop the world
                    break
        # recycle
        _broadcast.close()
        if self._state is not None:
            self._state.join()
        self._pool.shutdown()

    def _add_shell(self, shell: Shell, _broadcast: Broadcaster, _funcs: Dict[str, List[Function]]) -> None:
        """
        initialize shell data
        """
        name = shell.name()
        if name in _funcs:
            raise KeyError(f"Shell `{name}` already exists")
        _funcs[name] = shell.functions()
        event_types = shell.subscribing()
        ghost = self.GhostAdapter(self, name)
        chan_in = shell.on_sync(ghost)
        _broadcast.subscribe(name, chan_in, event_types)

    class GhostAdapter(Ghost[AbsState]):
        """
        Adapter to wrap the agent to the ghost
        """

        def __init__(self, agent: Agent, shell_name: str):
            self._agent = agent
            self._shell_name = shell_name

        def operate(self, op: Operator) -> Tuple[OperationType, str | None]:
            if self._agent._state is None:
                return "illegal", "agent is not ready"
            op.shell = self._shell_name
            return self._agent._state.operate(op)

        def state(self) -> AbsState:
            return self._agent._state

        def messages(self) -> Iterable[Message]:
            return self.state().conversation().messages()

# class ConversationShell(Shell):
#     """
#     non-block conversation item updater
#     """
#
#     def __init__(self, conversation: Conversation):
#         self._conversation = conversation
#         self._recv_queue = Queue()
#         self._closed = False
#         self._main_thread = Thread(target=self._main)
#
#     def name(self) -> str:
#         return "__conversation__"
#
#     def functions(self) -> List[Function]:
#         return []
#
#     def subscribing(self) -> List[str]:
#         return ServerEventType.conversation_item_events()
#
#     def on_sync(self, ghost: Ghost) -> ChanIn[Union[dict, None]]:
#         self._main_thread.start()
#         return self._recv_queue
#
#     def _main(self):
#         while not self._closed:
#             e = self._recv_queue.get(block=True)
#             if e is None:
#                 self._closed = True
#                 break
#             self._add_conversation(e)
#
#     def _add_conversation(self, e: dict) -> None:
#         raise NotImplementedError("todo")
#
#     def destroy(self):
#         self._main_thread.join()
