from typing import Optional, Iterable, List, TypeVar, Tuple, Union, Callable

from ghostos.container import Container
from ghostos.abcd import Conversation, Scope, Ghost, Context
from ghostos.abcd import run_session_event
from ghostos.errors import SessionError
from ghostos.core.messages import (
    Message, Role,
    Stream, Receiver, new_basic_connection,
)
from ghostos.core.runtime import (
    Event, EventTypes, EventBus,
    GoTaskStruct, TaskLocker, GoTasks, TaskState,
    GoThreadInfo, GoThreads,
)
from ghostos.contracts.pool import Pool
from ghostos.contracts.logger import LoggerItf
from ghostos.entity import to_entity_meta, get_entity
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
    ):
        self._conf = conf
        self.task_id = task.task_id
        self._container = Container(parent=container, name="conversation")
        self.logger = self._container.force_fetch(LoggerItf)
        self._scope = Scope(
            shell_id=task.shell_id,
            process_id=task.process_id,
            task_id=task.task_id,
            parent_task_id=task.parent,
        )
        self._pool = self._container.force_fetch(Pool)
        self._is_background = is_background
        self._ctx: Optional[Context] = None
        self._locker = task_locker
        self._tasks = container.force_fetch(GoTasks)
        self._threads = container.force_fetch(GoThreads)
        self._eventbus = container.force_fetch(EventBus)
        self._submit_session_thread: Optional[Thread] = None
        self._handling_event = False
        self._mutex = Lock()
        self._closed = False
        self._shell_closed = shell_closed
        self._bootstrap()

    def _bootstrap(self):
        providers = self.get_ghost_driver().providers()
        # bind self
        self._container.set(Conversation, self)
        for provider in providers:
            self._container.register(provider)
        self._container.bootstrap()

    def container(self) -> Container:
        self._validate_closed()
        return self._container

    def task(self) -> GoTaskStruct:
        self._validate_closed()
        return self._tasks.get_task(self._scope.task_id)

    def thread(self) -> GoThreadInfo:
        self._validate_closed()
        task = self.task()
        thread_id = task.thread_id
        return self._threads.get_thread(thread_id, create=True)

    def update_thread(self, thread: GoThreadInfo) -> None:
        self._validate_closed()
        task = self.task()
        thread.id = task.thread_id
        self._threads.save_thread(thread)

    def get_ghost(self) -> Ghost:
        self._validate_closed()
        task = self.task()
        return get_entity(task.meta, Ghost)

    def get_context(self) -> Optional[Context]:
        self._validate_closed()
        task = self.task()
        if task.context is None:
            return None
        return get_entity(task.context, Context)

    def get_instructions(self) -> str:
        self._validate_closed()
        session = self._create_session(self.task(), self._locker, None)
        try:
            instructions = session.get_instructions()
            return instructions
        finally:
            session.destroy()

    def get_artifact(self) -> Tuple[Union[Ghost.ArtifactType, None], TaskState]:
        self._validate_closed()
        task = self.task()
        session = self._create_session(task, self._locker, None)
        with session:
            return session.get_artifact(), TaskState(session.task.state)

    def talk(self, query: str, user_name: str = "") -> Tuple[Event, Receiver]:
        self._validate_closed()
        self.logger.debug("talk to user %s", user_name)
        message = Role.USER.new(content=query, name=user_name)
        return self.respond([message])

    def update_context(self, context: Context) -> None:
        self._validate_closed()
        self._ctx = context

    def respond(
            self,
            inputs: Iterable[Message],
            context: Optional[Ghost.ContextType] = None,
            history: Optional[List[Message]] = None,
    ) -> Tuple[Event, Receiver]:
        self._validate_closed()
        if self._submit_session_thread:
            self._submit_session_thread.join()
            self._submit_session_thread = None
        context_meta = to_entity_meta(context) if context is not None else None
        if self._ctx is not None:
            context_meta = to_entity_meta(self._ctx)
            self._ctx = None
        event = EventTypes.INPUT.new(
            task_id=self._scope.task_id,
            messages=list(inputs),
            context=context_meta,
            history=history,
        )
        return event, self.respond_event(event)

    def respond_event(
            self,
            event: Event,
            timeout: float = 0.0,
    ) -> Receiver:
        self._validate_closed()
        if self._handling_event:
            raise RuntimeError("conversation is handling event")
        # complete task_id
        if not event.task_id:
            event.task_id = self._scope.task_id
        self.logger.debug("start to respond event %s", event.event_id)

        stream, retriever = new_basic_connection(
            timeout=timeout,
            idle=self._conf.message_receiver_idle,
            complete_only=self._is_background,
        )
        self._submit_session_thread = Thread(target=self._submit_session_event, args=(event, stream,))
        self._submit_session_thread.start()
        return retriever

    def _validate_closed(self):
        if self._closed:
            raise RuntimeError(f"Conversation is closed")
        if self._shell_closed():
            raise RuntimeError(f"Shell is closed")

    def _submit_session_event(self, event: Event, stream: Stream) -> None:
        self.logger.debug("submit session event")
        try:
            self._handling_event = True
            with stream:
                task = self._tasks.get_task(event.task_id)
                session = self._create_session(task, self._locker, stream)
                self.logger.debug(
                    f"create session from event id %s, task_id is %s",
                    event.event_id, task.task_id,
                )
                with session:
                    run_session_event(session, event, self._conf.max_session_step)
        except Exception as e:
            if not self.fail(error=e):
                raise
        finally:
            self._eventbus.notify_task(event.task_id)
            self._handling_event = False
            self._submit_session_thread = None

    def _create_session(
            self,
            task: GoTaskStruct,
            locker: TaskLocker,
            stream: Optional[Stream],
    ) -> SessionImpl:
        return SessionImpl(
            container=self.container(),
            stream=stream,
            task=task,
            locker=locker,
            max_errors=self._conf.max_task_errors,
        )

    def pop_event(self) -> Optional[Event]:
        return self._eventbus.pop_task_event(self._scope.task_id)

    def send_event(self, event: Event) -> None:
        task = self._tasks.get_task(event.task_id)
        notify = True
        if task:
            notify = task.depth > 0
        self._eventbus.send_event(event, notify)

    def fail(self, error: Exception) -> bool:
        if self._closed:
            return False
        if isinstance(error, SessionError):
            self.logger.info(f"receive session stop error: {error}")
            return False
        elif isinstance(error, IOError):
            self.logger.exception(f"receive IO error: {error}")
            return False
        # otherwise, close the whole thing.
        self.logger.exception(f"receive IO error: {error}")
        self.close()
        return False

    def __del__(self):
        self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.logger.info("conversation %s is closing", self.task_id)
        self._handling_event = False
        if self._submit_session_thread:
            self._submit_session_thread.join()
            self._submit_session_thread = None
        self._locker.release()
        self._destroy()

    def _destroy(self):
        self.logger.info("conversation %s is destroying", self.task_id)
        self._container.destroy()
        del self._container
        del self._tasks
        del self._threads
        del self._eventbus
        del self._pool

    def closed(self) -> bool:
        return self._closed

    def available(self) -> bool:
        if self.closed() or self._shell_closed() or self._handling_event:
            return False
        return True
