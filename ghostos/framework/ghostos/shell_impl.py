import time
from typing import Union, Optional, Iterable, List, Tuple, TypeVar, Callable

from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.pool import Pool
from ghostos.container import Container, Provider
from ghostos.abcd import Shell, Conversation, Ghost, Scope, Background
from ghostos.abcd.utils import get_ghost_driver
from ghostos.core.messages import Message, Receiver
from ghostos.core.runtime import (
    Event, GoProcess, EventBus,
    GoTasks, TaskState, GoTaskStruct,
)
from ghostos.core.messages import Stream
from ghostos.helpers import uuid, Timeleft
from ghostos.identifier import get_identifier
from ghostos.entity import to_entity_meta
from pydantic import BaseModel, Field
from threading import Thread
from .conversation_impl import ConversationImpl, ConversationConf

__all__ = ['ShellConf', 'ShellImpl', 'Shell']


class ShellConf(BaseModel):
    max_session_steps: int = Field(
        default=10,
    )
    max_task_errors: int = Field(
        default=3,
    )
    background_idle_time: float = Field(1)
    task_lock_overdue: float = Field(
        default=10.0
    )


G = TypeVar("G", bound=Ghost)


class ShellImpl(Shell):

    def __init__(
            self,
            config: ShellConf,
            container: Container,
            process: GoProcess,
            providers: List[Provider],
    ):
        self._conf = config
        # prepare container
        for provider in providers:
            container.register(provider)
        self._container = container

        self._shell_id = process.shell_id
        self._process_id = process.process_id
        self._scope = Scope(
            shell_id=self._shell_id,
            process_id=self._process_id,
            task_id=self._process_id,
        )
        self._eventbus = container.force_fetch(EventBus)
        self._tasks = container.force_fetch(GoTasks)
        self._closed = False
        self._background_started = False
        self._logger = container.force_fetch(LoggerItf)
        # bootstrap the container.
        # bind self
        self._container.set(Shell, self)
        self._container.set(ShellImpl, self)
        self._container.set(ShellConf, config)
        self._container.bootstrap()

    def container(self) -> Container:
        return self._container

    def send_event(self, event: Event) -> None:
        task_id = event.task_id
        task = self._tasks.get_task(task_id)
        notify = True
        if task:
            notify = task.depth > 0
        self._eventbus.send_event(event, notify)

    def sync(self, ghost: Ghost, context: Optional[Ghost.ContextType] = None) -> Conversation:
        driver = get_ghost_driver(ghost)
        task_id = driver.make_task_id(self._scope)
        self._logger.debug("sync ghost with task id %s", task_id)

        task = self._tasks.get_task(task_id)
        if task is None:
            task = self.create_root_task(task_id, ghost, context)
            self._logger.debug("create root task task id %s for ghost", task_id)

        task.meta = to_entity_meta(ghost)
        if context is not None:
            task.context = to_entity_meta(context)
        conversation = self.sync_task(task, throw=True, is_background=False)
        return conversation

    def sync_task(
            self,
            task: GoTaskStruct,
            *,
            throw: bool,
            is_background: bool,
    ) -> Optional[Conversation]:
        locker = self._tasks.lock_task(task.task_id, self._conf.task_lock_overdue)
        if locker.acquire():
            conf = ConversationConf(
                max_session_steps=self._conf.max_session_steps,
                max_task_errors=self._conf.max_task_errors,
            )
            self._tasks.save_task(task)
            return ConversationImpl(
                conf=conf,
                container=Container(parent=self._container),
                task=task,
                task_locker=locker,
                is_background=is_background,
                shell_closed=self.closed,
            )
        elif throw:
            raise RuntimeError(f'Task {task.task_id} already locked')
        return None

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
        conversation = self.sync_task(task, throw=True, is_background=False)
        with conversation:
            e, r = conversation.respond(instructions)
            send_message(r)

            while timeleft.alive():
                task = conversation.task()
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

        conversation = self.sync_task(task, throw=False, is_background=True)
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
            pool = self.container().force_fetch(Pool)
            pool.submit(self._run_background_worker, background)

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
                self._logger.exception(err)
                break
            idle()
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
        pool = self.container().force_fetch(Pool)
        pool.shutdown()
        self._container.destroy()
        del self._container
        del self._eventbus
        del self._tasks
