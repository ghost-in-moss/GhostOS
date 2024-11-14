import time
from typing import Union, Optional, Iterable, List, Tuple, TypeVar

from ghostos.container import Container
from ghostos.core.abcd.concepts import Shell, Conversation, Ghost, Scope, Background
from ghostos.core.abcd.utils import get_ghost_driver
from ghostos.core.messages import Message, Receiver
from ghostos.core.runtime import (
    Event, GoProcess, EventBus,
    GoTasks, TaskState, GoTaskStruct,
)
from ghostos.core.messages import Stream
from ghostos.prompter import Prompter
from ghostos.container import Provider
from ghostos.helpers import uuid, Timeleft
from ghostos.identifier import get_identifier
from ghostos.entity import to_entity_meta
from ghostos.prompter import TextPrmt
from pydantic import BaseModel, Field
from threading import Thread
from .conversation_impl import ConversationImpl, ConversationConf


class ShellConf(BaseModel):
    persona: str = Field(
        description="the persona of the shell root agents",
    )
    max_session_steps: int = Field(
        default=10,
    )
    max_task_errors: int = Field(
        default=3,
    )
    background_idle_time: float = Field(0.5)


G = TypeVar("G", bound=Ghost)


class ShellImpl(Shell):

    def __init__(
            self,
            config: ShellConf,
            container: Container,
            process: GoProcess,
            *providers: Provider,
    ):
        self._conf = config
        # prepare container
        for provider in providers:
            container.register(provider)
        self._container = container
        # bind self
        self._container.set(Shell, self)
        self._container.set(ShellImpl, self)
        self._container.set(ShellConf, config)
        self._shell_id = process.shell_id
        self._process_id = process.process_id
        self._scope = Scope(
            shell_id=self._shell_id,
            process_id=self._process_id,
            task_id=self._process_id,
        )
        self._eventbus = container.force_fetch(EventBus)
        self._tasks = container.force_fetch(GoTasks)
        self._workers: List[Thread] = []
        self._closed = False
        self._background_started = False
        # bootstrap the container.
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

    def sync(self, ghost: G, context: Optional[G.Context] = None) -> Conversation:
        driver = get_ghost_driver(ghost)
        task_id = driver.make_task_id(self._scope)
        task = self._tasks.get_task(task_id)
        if task is None:
            task = self.create_root_task(ghost, context)
        task.meta = to_entity_meta(ghost)
        if context is not None:
            task.context = to_entity_meta(context)
        conversation = self.sync_task(task, throw=True, is_background=False)
        if context is not None:
            return conversation
        raise RuntimeError(f'Cannot sync ghost')

    def sync_task(
            self,
            task: GoTaskStruct,
            *,
            throw: bool,
            is_background: bool,
    ) -> Optional[Conversation]:
        locker = self._tasks.lock_task(task.task_id)
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
            )
        elif throw:
            raise RuntimeError(f'Task {task.task_id} already locked')
        return None

    def call(
            self,
            ghost: G,
            context: Optional[G.Context] = None,
            instructions: Optional[Iterable[Message]] = None,
            timeout: float = 0.0,
            stream: Optional[Stream] = None,
    ) -> Tuple[Union[G.Artifact, None], TaskState]:

        def send_message(receiver: Receiver):
            with receiver:
                if stream:
                    stream.send(receiver.recv())
                else:
                    receiver.wait()

        timeleft = Timeleft(timeout)
        task = self.create_root_task(ghost, context)
        conversation = self.sync_task(task, throw=True, is_background=False)
        with conversation:
            r = conversation.respond(instructions)
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
                    conversation.ask("continue to fulfill your task or fail")
            return conversation.get_artifact()

    def create_root_task(
            self,
            ghost: G,
            context: Optional[G.Context],
    ) -> GoTaskStruct:
        task_id = uuid()
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
                background.on_event(e, r)

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

    def background_run(self, worker: int = 4, background: Optional[Background] = None) -> None:
        self._validate_closed()
        if self._background_started:
            raise RuntimeError(f'background run already started')

        for i in range(worker):
            t = Thread(target=self._run_background_worker, args=(background,))
            t.start()
            self._workers.append(t)

    def _run_background_worker(self, background: Optional[Background] = None):
        def is_stopped() -> bool:
            if self._closed:
                return True
            if background:
                return background.stopped()
            return False

        def idle():
            time.sleep(self._conf.background_idle_time)

        def halt() -> bool:
            if background:
                halt_time = background.halt()
                if halt_time > 0:
                    time.sleep(halt_time)
                    return True
            return False

        while not is_stopped():
            if halt():
                continue
            try:
                handled_event = self.run_background_event(background)
                if handled_event:
                    continue
            except Exception as err:
                self.close()
                return
            idle()

    def _validate_closed(self):
        if self._closed:
            raise RuntimeError(f'Shell is closed')

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._workers:
            for t in self._workers:
                t.join()
        self._container.destroy()
        del self._container
        del self._workers
        del self._eventbus
        del self._tasks
