from typing import Optional, Iterable, List, TypeVar, Tuple, Union, Callable, Dict

from ghostos_container import Container
from ghostos.abcd import Conversation, Scope, Ghost, Context, EntityType
from ghostos.abcd import default_init_event_operator
from ghostos.errors import SessionError
from ghostos.contracts.variables import Variables
from ghostos.core.messages import (
    Message, Role, MessageKind, MessageKindParser,
    Stream, Receiver, new_basic_connection, ListReceiver,
)
from ghostos.core.runtime import (
    Event, EventTypes, EventBus,
    GoTaskStruct, TaskLocker, GoTasks, TaskState,
    GoThreadInfo, GoThreads,
)
from ghostos.core.llms import LLMFunc
from ghostos.contracts.pool import Pool
from ghostos.contracts.logger import LoggerItf, wrap_logger
from ghostos_common.entity import to_entity_meta, get_entity
from pydantic import BaseModel, Field
from .session_impl import SessionImpl
from threading import Lock, Thread

__all__ = ["ConversationImpl", "ConversationConf", "Conversation"]


class ConversationConf(BaseModel):
    message_receiver_idle: float = Field(
        0.05,
        description="The time in seconds to wait between retrievals",
    )
    max_session_step: int = Field(
        10,
        description="The maximum number of steps to run session event",
    )
    max_task_errors: int = Field(
        3,
        description="The maximum error number of task",
    )


G = TypeVar("G", bound=Ghost)


class ConversationImpl(Conversation[G]):

    def __init__(
            self,
            conf: ConversationConf,
            container: Container,
            task: GoTaskStruct,
            task_locker: TaskLocker,
            is_background: bool,
            shell_closed: Callable[[], bool],
            username: str = "",
            user_role: str = Role.USER.value,
    ):
        self._closed = False
        self._conf = conf
        self.task_id = task.task_id
        self._container = Container(parent=container, name="conversation")
        self._username = username
        self._user_role = user_role
        variables = self._container.force_fetch(Variables)
        self._message_parser = MessageKindParser(
            variables,
            name=self._username,
            role=self._user_role,
        )

        self.scope = Scope(
            shell_id=task.shell_id,
            process_id=task.process_id,
            task_id=task.task_id,
            parent_task_id=task.parent,
        )
        self.logger = wrap_logger(
            self._container.force_fetch(LoggerItf),
            dict(scope=self.scope.model_dump(exclude_defaults=True)),
        )

        self._pool = self._container.force_fetch(Pool)
        self._is_background = is_background
        self._ctx: Optional[Context] = None
        self._task_locker = task_locker
        self._tasks = container.force_fetch(GoTasks)
        self._threads = container.force_fetch(GoThreads)
        self._eventbus = container.force_fetch(EventBus)
        self._submit_session_thread: Optional[Thread] = None
        self._handling_event = False
        self._mutex = Lock()
        self._shell_closed = shell_closed
        self._bootstrap()

    def _bootstrap(self):
        # bind self
        self._container.set(Conversation, self)
        self._container.bootstrap()

    def container(self) -> Container:
        self._validate_closed()
        return self._container

    def get_task(self) -> GoTaskStruct:
        self._validate_closed()
        return self._tasks.get_task(self.scope.task_id)

    def get_state_values(self) -> Dict[str, EntityType]:
        from ghostos_common.entity import from_entity_meta
        self._validate_closed()
        values = {}
        metas = self.get_task().state_values
        for key, meta in metas.items():
            values[key] = from_entity_meta(meta)
        return values

    def get_thread(self, truncated: bool = False) -> GoThreadInfo:
        self._validate_closed()
        task = self.get_task()
        if not truncated:
            thread_id = task.thread_id
            return self._threads.get_thread(thread_id, create=True)
        session = self._create_session(task, None)
        return session.get_truncated_thread()

    def update_thread(self, thread: GoThreadInfo) -> None:
        self.refresh()
        self._validate_closed()
        task = self.get_task()
        task.thread_id = thread.id
        # change the thread id of the task
        # and save task and thread
        self._threads.save_thread(thread)
        self._tasks.save_task(task)

    def get_ghost(self) -> Ghost:
        self._validate_closed()
        task = self.get_task()
        return get_entity(task.meta, Ghost)

    def get_context(self) -> Optional[Context]:
        self._validate_closed()
        task = self.get_task()
        if task.context is None:
            return None
        return get_entity(task.context, Context)

    def get_functions(self) -> List[LLMFunc]:
        self.refresh()
        self._validate_closed()
        session = self._create_session(self.get_task(), None)
        actions = self.get_ghost_driver().actions(session)
        functions = []
        for action in actions:
            function = action.as_function()
            if function is not None:
                functions.append(function)
        return functions

    def get_system_instruction(self) -> str:
        self.refresh()
        self._validate_closed()
        session = self._create_session(self.get_task(), None)
        with session:
            instructions = session.get_system_instructions()
            return instructions

    def refresh(self) -> bool:
        self._validate_closed()
        ok = self._task_locker.refresh()
        if not ok:
            self.close()
        return ok

    def get_artifact(self) -> Tuple[Union[Ghost.ArtifactType, None], TaskState]:
        self._validate_closed()
        task = self.get_task()
        session = self._create_session(task, None)
        with session:
            return session.get_artifact(), TaskState(session.task.state)

    def talk(
            self,
            query: str,
            context: Optional[Ghost.ContextType] = None,
            *,
            user_name: str = "",
            timeout: float = 0.0,
            request_timeout: float = 0.0,
    ) -> Tuple[Event, Receiver]:
        self._validate_closed()
        self.logger.debug("talk to user %s", user_name)
        message = Role.USER.new(content=query, name=user_name)
        return self.respond([message], context, timeout=timeout, request_timeout=request_timeout)

    def update_context(self, context: Context) -> None:
        self._validate_closed()
        self._ctx = context

    def respond(
            self,
            inputs: Iterable[MessageKind],
            context: Optional[Ghost.ContextType] = None,
            *,
            streaming: bool = True,
            timeout: float = 0.0,
            request_timeout: float = 0.0,
    ) -> Tuple[Event, Receiver]:
        self._validate_closed()
        if self._submit_session_thread:
            self._submit_session_thread.join()
            self._submit_session_thread = None
        messages = list(self._message_parser.parse(inputs))
        context_meta = to_entity_meta(context) if context is not None else None
        if self._ctx is not None:
            context_meta = to_entity_meta(self._ctx)
            self._ctx = None
        event = EventTypes.INPUT.new(
            task_id=self.scope.task_id,
            messages=messages,
            context=context_meta,
        )
        return event, self.respond_event(event, streaming=streaming, timeout=timeout, request_timeout=request_timeout)

    def respond_event(
            self,
            event: Event,
            *,
            timeout: float = 0.0,
            request_timeout: float = 0.0,
            streaming: bool = True,
    ) -> Receiver:
        self.refresh()
        self._validate_closed()
        if event.task_id != self.task_id:
            self.send_event(event)
            return ListReceiver([])

        if self._handling_event:
            raise RuntimeError("conversation is handling event")
        # complete task_id
        if not event.task_id:
            event.task_id = self.scope.task_id
        self.logger.debug("start to respond event %s", event.event_id)

        stream, retriever = new_basic_connection(
            timeout=timeout,
            idle=self._conf.message_receiver_idle,
            complete_only=self._is_background or not streaming,
            request_timeout=request_timeout,
        )
        if self._submit_session_thread:
            self._submit_session_thread.join()
            self._submit_session_thread = None
        self._submit_session_thread = Thread(target=self._submit_session_event, args=(event, stream,))
        self._submit_session_thread.start()
        return retriever

    def _validate_closed(self):
        # todo: change error to defined error
        if self._closed:
            raise RuntimeError(f"Conversation is closed")
        if self._shell_closed():
            raise RuntimeError(f"Shell is closed")

    def _submit_session_event(self, event: Event, stream: Stream) -> None:
        with self._mutex:
            self._handling_event = True
            self.logger.debug("submit session event")
            try:
                with stream:
                    task = self._tasks.get_task(event.task_id)
                    session = self._create_session(task, stream)
                    self.logger.debug(
                        f"create session from event id %s, task_id is %s",
                        event.event_id, task.task_id,
                    )
                    with session:
                        self.loop_session_event(session, event, self._conf.max_session_step)
            except Exception as e:
                if not self.fail(error=e):
                    raise
            finally:
                if task and task.shall_notify():
                    self._eventbus.notify_task(event.task_id)
                self._handling_event = False
                self._submit_session_thread = None

    def loop_session_event(self, session: SessionImpl, event: Event, max_step: int) -> None:
        op = default_init_event_operator(event)
        step = 0
        while op is not None:
            step += 1
            if step > max_step:
                raise RuntimeError(f"Max step {max_step} reached")
            if not session.refresh(True):
                raise RuntimeError("Session refresh failed")
            self.logger.debug("start session op %s", repr(op))
            next_op = op.run(session)
            self.logger.debug("done session op %s", repr(op))
            op.destroy()
            # session do save after each op
            session.save()
            op = next_op

    def _create_session(
            self,
            task: GoTaskStruct,
            stream: Optional[Stream],
    ) -> SessionImpl:
        return SessionImpl(
            container=self.container(),
            logger=self.logger,
            scope=self.scope,
            stream=stream,
            task=task,
            refresh_callback=self.refresh,
            alive_check=self.is_alive,
            max_errors=self._conf.max_task_errors,
        )

    def pop_event(self) -> Optional[Event]:
        if self.available():
            return self._eventbus.pop_task_event(self.scope.task_id)
        return None

    def send_event(self, event: Event) -> None:
        self._validate_closed()
        task = self._tasks.get_task(event.task_id)
        notify = True
        if task:
            notify = task.depth > 0
        self._eventbus.send_event(event, notify)

    def fail(self, error: Exception) -> bool:
        if self._closed:
            return False
        if isinstance(error, SessionError):
            self.logger.info(f"conversation {self.task_id} receive session stop error: {error}")
            return False
        elif isinstance(error, IOError):
            self.logger.exception(f"conversation {self.task_id} receive IO error: {error}")
            return False
        # otherwise, close the whole thing.
        self.logger.exception(f"conversation {self.task_id} receive runtime error: {error}")
        self.close()
        return False

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.logger.info("conversation %s is closing", self.task_id)
        self._handling_event = False
        if self._submit_session_thread:
            self._submit_session_thread = None
        self.logger.info("conversation %s is destroying", self.task_id)
        self._container.shutdown()
        self._container = None
        if self._task_locker.acquired():
            self.logger.info("task %s is released", self.task_id)
            self._task_locker.release()

    def is_closed(self) -> bool:
        return self._closed or self._shell_closed()

    def is_alive(self) -> bool:
        return not self._closed

    def available(self) -> bool:
        if self.is_closed() or self._shell_closed() or self._handling_event:
            return False
        return True
