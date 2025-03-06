import time
from typing import Union, Optional, Iterable, List, Tuple, TypeVar, Callable
from ghostos.contracts.logger import LoggerItf, get_ghostos_logger
from ghostos.contracts.pool import Pool, DefaultPool
from ghostos_container import Container, Provider
from ghostos.abcd import Matrix, Conversation, Ghost, Scope, Background
from ghostos.abcd.utils import get_ghost_driver
from ghostos.core.messages import Message, Receiver, Role
from ghostos.core.runtime import (
    Event, GoProcess, EventBus,
    GoTasks, TaskState, GoTaskStruct,
)
from ghostos.core.messages import Stream
from ghostos_common.helpers import uuid, Timeleft, import_from_path
from ghostos_common.identifier import get_identifier
from ghostos_common.entity import to_entity_meta
from threading import Lock
from pydantic import BaseModel, Field
from .conversation_impl import ConversationImpl, ConversationConf

__all__ = ['MatrixConf', 'MatrixImpl', 'Matrix']


class MatrixConf(BaseModel):
    max_session_steps: int = Field(
        default=10,
    )
    max_task_errors: int = Field(
        default=3,
    )
    pool_size: int = 100
    background_idle_time: float = Field(1)
    task_lock_overdue: float = Field(
        default=10.0
    )
    providers: List[str] = []


G = TypeVar("G", bound=Ghost)


class MatrixImpl(Matrix):

    def __init__(
            self,
            config: MatrixConf,
            container: Container,
            process: GoProcess,
            providers: List[Provider],
    ):
        self._conversation_mutex = Lock()
        self._conf = config
        self._container = Container(parent=container, name="shell")
        # prepare container
        for provider in providers:
            self._container.register(provider)
        for provider_name in config.providers:
            p = import_from_path(provider_name)
            if isinstance(p, Provider):
                self._container.register(p)
            elif issubclass(p, Provider):
                self._container.register(p())

        self._shell_id = process.shell_id
        self._process_id = process.process_id
        self._scope = Scope(
            shell_id=self._shell_id,
            process_id=self._process_id,
            task_id=self._process_id,
        )
        self._pool = DefaultPool(config.pool_size)
        self._container.set(Pool, self._pool)
        self._eventbus = self._container.force_fetch(EventBus)
        self._tasks = self._container.force_fetch(GoTasks)
        self._closed = False
        self._background_started = False
        # bootstrap the container.
        # bind self
        self._container.set(Matrix, self)
        self._container.set(MatrixImpl, self)
        self._container.set(MatrixConf, config)
        self._container.bootstrap()
        self._conversations: List[Conversation] = []

    @property
    def logger(self) -> LoggerItf:
        return get_ghostos_logger()

    def container(self) -> Container:
        return self._container

    def send_event(self, event: Event) -> None:
        task_id = event.task_id
        task = self._tasks.get_task(task_id)
        notify = True
        if task:
            notify = task.depth > 0
        self._eventbus.send_event(event, notify)

    def sync(
            self,
            ghost: Ghost,
            context: Optional[Ghost.ContextType] = None,
            *,
            username: str = "",
            user_role: str = Role.USER.value,
            task_id: str = None,
            force: bool = False,
    ) -> Conversation:
        task = self.get_or_create_task(ghost, context, always_create=False, save=False, task_id=task_id)
        conversation = self._sync_task(
            task,
            throw=True,
            is_background=False,
            username=username,
            user_role=user_role,
            force=force,
        )
        return conversation

    def tasks(self) -> GoTasks:
        return self._tasks

    def eventbus(self) -> EventBus:
        return self._eventbus

    def get_or_create_task(
            self,
            ghost: Ghost,
            context: Optional[Ghost.ContextType] = None,
            *,
            task_id: str = None,
            always_create: bool = True,
            save: bool = False,
    ) -> GoTaskStruct:
        driver = get_ghost_driver(ghost)
        if not task_id:
            task_id = driver.make_task_id(self._scope)
        task = self._tasks.get_task(task_id)
        if task is None or always_create:
            task = self.create_root_task(task_id, ghost, context)
            self.logger.debug("create root task task id %s for ghost", task_id)
        task.meta = to_entity_meta(ghost)
        if context is not None:
            task.context = to_entity_meta(context)
        if save:
            self._tasks.save_task(task)
        return task

    def sync_task(
            self,
            task: Union[str, GoTaskStruct],
            *,
            username: str = "",
            user_role: str = "",
            force: bool = False,
    ) -> Conversation:
        if isinstance(task, str):
            task_id = task
            task = None
        elif isinstance(task, GoTaskStruct):
            task_id = task.task_id
        else:
            raise AttributeError(f'task {task} is not a str or GoTaskStruct')

        if task is None:
            task = self._tasks.get_task(task_id)

        if task is None:
            raise AttributeError(f'task {task_id} does not exist')
        return self._sync_task(
            task,
            throw=True,
            is_background=False,
            username=username,
            user_role=user_role,
            force=force,
        )

    def _sync_task(
            self,
            task: GoTaskStruct,
            *,
            throw: bool,
            is_background: bool,
            username: str = "",
            user_role: str = "",
            force: bool = False,
    ) -> Optional[Conversation]:
        locker = self._tasks.lock_task(task.task_id, self._conf.task_lock_overdue, force)
        if locker.acquire():
            conf = ConversationConf(
                max_session_steps=self._conf.max_session_steps,
                max_task_errors=self._conf.max_task_errors,
            )
            self._tasks.save_task(task)
            conversation = ConversationImpl(
                conf=conf,
                container=self._container,
                task=task,
                task_locker=locker,
                is_background=is_background,
                shell_closed=self.closed,
                username=username,
                user_role=user_role,
            )
            self._join_conversation(conversation)
            return conversation
        elif throw:
            raise RuntimeError(f'create conversation failed, Task {task.task_id} already locked')
        return None

    def _join_conversation(self, conversation: Conversation):
        with self._conversation_mutex:
            exists = self._conversations
            running = []
            # remove closed ones
            for c in exists:
                if c.is_closed():
                    continue
                running.append(c)
            running.append(conversation)
            self._conversations = running

    def call(
            self,
            ghost: Ghost,
            context: Optional[Ghost.ContextType] = None,
            instructions: Optional[Iterable[Message]] = None,
            timeout: float = 0.0,
            stream: Optional[Stream] = None,
    ) -> Tuple[Union[Ghost.ArtifactType, None], TaskState]:

        def send_message(receiver: Receiver):
            with receiver:
                if stream:
                    stream.send(receiver.recv())
                else:
                    receiver.wait()

        timeleft = Timeleft(timeout)
        task_id = uuid()
        task = self.create_root_task(task_id, ghost, context)
        conversation = self._sync_task(task, throw=True, is_background=False)
        if conversation is None:
            raise RuntimeError('create conversation failed')
        with conversation:
            e, r = conversation.respond(instructions)
            send_message(r)

            while timeleft.alive():
                task = conversation.get_task()
                if task.is_dead():
                    break
                e = conversation.pop_event()
                if e is not None:
                    r = conversation.respond_event(e)
                    send_message(r)
                else:
                    conversation.talk("continue to fulfill your task or fail")
            return conversation.get_artifact()

    def create_root_task(
            self,
            task_id: str,
            ghost: Ghost,
            context: Optional[Ghost.ContextType],
    ) -> GoTaskStruct:
        id_ = get_identifier(ghost)
        context_meta = to_entity_meta(context) if context else None
        task = GoTaskStruct.new(
            task_id=task_id,
            shell_id=self._scope.shell_id,
            process_id=self._scope.process_id,
            depth=0,
            name=id_.name,
            description=id_.description,
            meta=to_entity_meta(ghost),
            context=context_meta,
            parent_task_id=None,
        )
        self._tasks.save_task(task)
        return task

    def run_background_event(
            self,
            background: Optional[Background] = None,
    ) -> Union[Event, None]:
        self._validate_closed()
        task_id = self._eventbus.pop_task_notification()
        if task_id is None:
            return None

        task = self._tasks.get_task(task_id)
        if task is None:
            self._eventbus.clear_task(task_id)
            return None

        conversation = self._sync_task(task, throw=False, is_background=True)
        if conversation is None:
            return None

        def on_event(e: Event, r: Receiver) -> None:
            if background:
                messages = r.wait()
                tails = []
                for message in messages:
                    if message.is_complete():
                        tails.append(message)
                background.on_event(e, tails)

        with conversation:
            event = conversation.pop_event()
            if event is None:
                return None
            try:
                receiver = conversation.respond_event(event)
                with receiver:
                    on_event(event, receiver)
                    receiver.wait()
                    return event
            except Exception as err:
                if background:
                    intercepted = background.on_error(err)
                    if not intercepted:
                        raise
            finally:
                self._eventbus.notify_task(self._scope.task_id)

    def submit(self, caller: Callable, *args, **kwargs):
        pool = self.container().force_fetch(Pool)
        pool.submit(caller, *args, **kwargs)

    def background_run(self, worker: int = 4, background: Optional[Background] = None) -> None:
        self._validate_closed()
        if self._background_started:
            raise RuntimeError(f'background run already started')

        for i in range(worker):
            self._pool.submit(self._run_background_worker, background)

    def _run_background_worker(self, background: Optional[Background] = None):
        def is_stopped() -> bool:
            if self._closed:
                return True
            if background:
                return not background.alive()
            return False

        def idle():
            time.sleep(self._conf.background_idle_time)

        def halt() -> int:
            if background:
                return background.halt()
            return 0

        while not is_stopped():
            if halt_time := halt():
                time.sleep(halt_time)
                continue
            try:
                handled_event = self.run_background_event(background)
                if handled_event:
                    continue
            except Exception as err:
                self.logger.exception(err)
                if background and not background.on_error(err):
                    self.logger.info("stop shell due to background not catch error")
                    break
            idle()
        self.logger.info("shut down background worker")
        self.close()

    def _validate_closed(self):
        if self._closed:
            raise RuntimeError(f'Shell is closed')

    def closed(self) -> bool:
        return self._closed

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.logger.info(
            "start closing shell %s, conversations %d",
            self._shell_id,
            len(self._conversations)
        )
        for conversation in self._conversations:
            self.logger.info("closing shell conversation %s", conversation.task_id)
            conversation.close()
        self.logger.info("shell conversations are closed")
        self._container.shutdown()
        self.logger.info("shell container destroyed")
        self.logger.info("shutting down shell pool")
        self._pool.shutdown(cancel_futures=True)
        self.logger.info("shell pool is shut")
