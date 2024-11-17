from typing import Optional, Iterable, List, TypeVar, Tuple, Union

from ghostos.container import Container
from ghostos.abcd import Conversation, Scope, Ghost
from ghostos.abcd import run_session_event
from ghostos.core.messages import (
    Message, Role,
    Stream, Receiver, new_arr_connection,
)
from ghostos.core.runtime import (
    Event, EventTypes, EventBus,
    GoTaskStruct, TaskLocker, GoTasks, TaskState,
    GoThreadInfo, GoThreads,
)
from ghostos.contracts.pool import Pool
from ghostos.contracts.logger import LoggerItf, wrap_logger
from ghostos.entity import to_entity_meta
from pydantic import BaseModel, Field
from .session_impl import SessionImpl

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
    ):
        self._conf = conf
        self._container = container
        self._scope = Scope(
            shell_id=task.shell_id,
            process_id=task.process_id,
            task_id=task.task_id,
            parent_task_id=task.parent,
        )
        self._pool = self._container.force_fetch(Pool)
        logger = container.force_fetch(LoggerItf)
        self._logger = wrap_logger(logger, self._scope.model_dump())
        self._is_background = is_background
        self._locker = task_locker
        self._tasks = container.force_fetch(GoTasks)
        self._threads = container.force_fetch(GoThreads)
        self._eventbus = container.force_fetch(EventBus)
        self._closed = False
        self._bootstrap()

    def _bootstrap(self):
        self._container.set(LoggerItf, self._logger)
        self._container.bootstrap()

    def container(self) -> Container:
        self._validate_closed()
        return self._container

    def task(self) -> GoTaskStruct:
        return self._tasks.get_task(self._scope.task_id)

    def thread(self) -> GoThreadInfo:
        task = self.task()
        thread_id = task.thread_id
        return self._threads.get_thread(thread_id, create=True)

    def get_artifact(self) -> Tuple[Union[Ghost.ArtifactType, None], TaskState]:
        task = self.task()
        session = self._create_session(task, self._locker, None)
        with session:
            return session.get_artifact(), TaskState(session.task.state)

    def talk(self, query: str, user_name: str = "") -> Receiver:
        message = Role.USER.new(content=query, name=user_name)
        return self.respond([message])

    def respond(
            self,
            inputs: Iterable[Message],
            context: Optional[Ghost.ContextType] = None,
            history: Optional[List[Message]] = None,
    ) -> Receiver:
        self._validate_closed()
        context_meta = to_entity_meta(context) if context is not None else None
        event = EventTypes.INPUT.new(
            task_id=self._scope.task_id,
            messages=list(inputs),
            context=context_meta,
            history=history,
        )
        return self.respond_event(event)

    def respond_event(
            self,
            event: Event,
            timeout: float = 0.0,
    ) -> Receiver:
        self._validate_closed()
        stream, retriever = new_arr_connection(
            timeout=timeout,
            idle=self._conf.message_receiver_idle,
            complete_only=self._is_background,
        )
        self._pool.submit(self._submit_session_event, event, stream)
        return retriever

    def _validate_closed(self):
        if self._closed:
            raise RuntimeError(f"Conversation is closed")

    def _submit_session_event(self, event: Event, stream: Stream) -> None:
        with stream:
            task = self._tasks.get_task(event.task_id)
            session = self._create_session(task, self._locker, stream)
            with session:
                try:
                    run_session_event(session, event, self._conf.max_session_step)
                    self._eventbus.notify_task(event.task_id)
                except Exception as e:
                    self.fail(error=e)

    def _create_session(
            self,
            task: GoTaskStruct,
            locker: TaskLocker,
            stream: Optional[Stream],
    ) -> SessionImpl:
        container = Container(parent=self._container)
        return SessionImpl(
            container=container,
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
        self.close()
        return False

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._locker.release()
        self._destroy()

    def _destroy(self):
        self._container.destroy()
        del self._container
        del self._tasks
        del self._threads
        del self._eventbus
        del self._pool
        del self._logger

    def closed(self) -> bool:
        return self._closed
