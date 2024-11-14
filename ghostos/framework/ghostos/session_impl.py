from typing import Optional, List, Iterable, Tuple, TypeVar, Dict, Union, Any

from ghostos.core.abcd.concepts import (
    Session, Ghost, GhostDriver, Shell, Scope, Taskflow, Operator, Subtasks
)
from ghostos.core.abcd.utils import get_ghost_driver
from ghostos.core.messages import (
    MessageKind, Message, Caller, Stream, Role, MessageKindParser, MessageType
)
from ghostos.core.runtime import (
    TaskBrief, GoTaskStruct, TaskLocker, TaskPayload, GoTasks, TaskState,
    EventBus, Event, EventTypes,
    GoThreads,
    Messenger, GoThreadInfo,
)
from ghostos.prompter import Prompter
from ghostos.contracts.logger import wrap_logger, LoggerItf
from ghostos.contracts.variables import Variables
from ghostos.container import Container, provide, Contracts
from ghostos.entity import to_entity_meta, from_entity_meta, get_entity, EntityType
from ghostos.identifier import get_identifier
from ghostos.framework.messengers import DefaultMessenger
from .taskflow_impl import TaskflowImpl
from .subtasks_impl import SubtasksImpl

G = TypeVar("G", bound=Ghost)


class EmptyOperator(Operator):

    def run(self, session: Session) -> Union[Operator, None]:
        return None

    def destroy(self):
        pass


class SessionImpl(Session[G]):
    contracts = Contracts([
        GoThreads,
        GoTasks,
        EventBus,
    ])

    def __init__(
            self,
            container: Container,
            stream: Optional[Stream],
            task: GoTaskStruct,
            locker: TaskLocker,
            max_errors: int,
    ):
        # session level container
        self.container = container
        self.upstream = stream
        self.task = task
        self.locker = locker
        threads = container.force_fetch(GoThreads)
        thread = threads.get_thread(task.thread_id, create=True)
        self.thread = thread
        self.scope = Scope(
            shell_id=task.shell_id,
            process_id=task.process_id,
            task_id=task.task_id,
            parent_task_id=task.parent_task_id,
        )
        logger = container.force_fetch(LoggerItf)
        self.logger = wrap_logger(
            logger,
            extra=self.scope.model_dump(),
        )

        self.ghost: G = get_entity(self.task.meta, Ghost)
        self.ghost_driver: GhostDriver[G] = self.ghost.Driver(self.ghost)
        identifier = get_identifier(self.ghost)
        variables = container.force_fetch(Variables)
        self._message_parser = MessageKindParser(
            variables,
            name=identifier.name,
            role=Role.ASSISTANT.value,
        )
        self.state = self.unmarshal_state(task)
        self._max_errors = max_errors
        self._fetched_task_briefs: Dict[str, TaskBrief] = {}
        self._creating_tasks: Dict[str, GoTaskStruct] = {}
        self._firing_events: List[Event] = []
        self._saving_threads: Dict[str, GoThreadInfo] = {}
        self._failed = False
        self._done = False
        self._destroyed = False
        self._bootstrap()
        if not self.refresh():
            raise RuntimeError(f"Failed to start session")

    def _bootstrap(self):
        self.contracts.validate(self.container)
        self.container.set(Session, self)
        self.container.set(LoggerItf, self.logger)
        self.container.set(Scope, self.scope)
        self.container.set(MessageKindParser, self._message_parser)
        self.container.register(provide(GoTaskStruct, False)(lambda c: self.task))
        self.container.register(provide(GoThreadInfo, False)(lambda c: self.thread))
        self.container.register(provide(Taskflow, False)(lambda c: self.taskflow()))
        self.container.register(provide(Subtasks, False)(lambda c: self.subtasks()))
        self.container.register(provide(Messenger, False)(lambda c: self.messenger()))
        self.container.bootstrap()

    @staticmethod
    def unmarshal_state(task: GoTaskStruct) -> Dict[str, EntityType]:
        state_values = {}
        for key, entity_meta in task.state_values.items():
            entity = from_entity_meta(entity_meta)
            state_values[key] = entity
        return state_values

    def is_alive(self) -> bool:
        if self._failed or self._destroyed:
            return False
        return self.locker.acquired() and self.upstream.alive()

    def _validate_alive(self):
        if not self.is_alive():
            raise RuntimeError(f"Session is not alive")

    def to_messages(self, values: Iterable[Union[MessageKind, Any]]) -> List[Message]:
        return list(self._message_parser.parse(values))

    def parse_event(self, event: Event) -> Tuple[Optional[Event], Optional[Operator]]:
        self._validate_alive()
        driver = get_ghost_driver(self.ghost)
        # always let ghost driver decide event handling logic first.
        event = driver.parse_event(self, event)
        if event is None:
            return None, None
        # notification do not trigger the handling
        if EventTypes.NOTIFY.value == event.type:
            self.thread.new_turn(event)
            return None, None

        if EventTypes.INPUT.value == event.type:
            # only input event can reset errors.
            self.task.errors = 0
            if event.context is not None:
                self.task.context = event.context
            if event.history:
                self.thread = self.thread.reset_history(event.history)
                event.history = []

        # other event
        elif self.task.is_dead():
            # dead task can only respond event from parent input.
            self.thread.new_turn(event)
            return None, EmptyOperator()

        if EventTypes.ERROR.value == event.type:
            self.task.error += 1
            if self.task.errors > self._max_errors:
                # if reach max errors, fail the task
                return None, self.taskflow().fail("task failed too much, exceeds max errors")

        if EventTypes.CANCEL.value == event.type:
            # cancel self and all subtasks.
            self.task.errors = 0
            self.thread.new_turn(event)
            self.task.state = TaskState.CANCELLED
            for child_id in self.task.children:
                event = EventTypes.CANCEL.new(
                    task_id=child_id,
                    messages=[],
                    from_task_id=self.task.task_id,
                    from_task_name=self.task.name,
                    reason="parent task is canceled",
                    instruction="cancel what you are doing",
                )
                self.fire_events(event)
            return None, EmptyOperator()

        event.history = []
        event.context = None
        return event, None

    def taskflow(self) -> Taskflow:
        self._validate_alive()
        return TaskflowImpl(self, self._message_parser)

    def subtasks(self) -> Subtasks:
        return SubtasksImpl(self)

    def get_context(self) -> Optional[Prompter]:
        if self.task.context is None:
            return None
        return get_entity(self.task.context, Prompter)

    def get_artifact(self) -> G.Artifact:
        return self.ghost_driver.get_artifact(self)

    def refresh(self) -> bool:
        if self._failed or self._destroyed or not self.is_alive():
            return False
        return self.locker.refresh()

    def _reset(self):
        self._fetched_task_briefs = {}
        self._firing_events = []
        self._creating_tasks = {}
        self._saving_threads = {}
        self.task = self.task.new_turn()

    def messenger(self) -> Messenger:
        self._validate_alive()
        task_payload = TaskPayload.from_task(self.task)
        identity = get_identifier(self.ghost)
        return DefaultMessenger(
            upstream=self.upstream,
            name=identity.name,
            role=Role.ASSISTANT.value,
            payloads=[task_payload],
        )

    def respond(self, messages: Iterable[MessageKind], remember: bool = True) -> Tuple[List[Message], List[Caller]]:
        self._validate_alive()
        messenger = self.messenger()
        messenger.send(messages)
        messages, callers = messenger.flush()
        if remember:
            self.thread.append(*messages)
        return messages, callers

    def cancel_subtask(self, ghost: G, reason: str = "") -> None:
        self._validate_alive()
        driver = get_ghost_driver(ghost)
        task_id = driver.make_task_id(self.scope)
        tasks = self.container.force_fetch(GoTasks)
        subtask = tasks.get_task(task_id)
        if subtask is None:
            return
        event = EventTypes.CANCEL.new(
            task_id=task_id,
            reason=reason,
            messages=[],
            from_task_id=self.task.task_id,
            from_task_name=self.task.name,
        )
        self.fire_events(event)

    def create_tasks(self, *tasks: GoTaskStruct) -> None:
        self._validate_alive()
        for task in tasks:
            self._creating_tasks[task.task_id] = task

    def create_threads(self, *threads: GoThreadInfo) -> None:
        self._validate_alive()
        for t in threads:
            self._saving_threads[t.id] = t

    def call(self, ghost: G, ctx: G.Props) -> G.Artifact:
        self._validate_alive()
        shell = self.container.force_fetch(Shell)
        return shell.call(ghost, ctx)

    def fire_events(self, *events: "Event") -> None:
        self._validate_alive()
        self._firing_events.extend(events)

    def get_task_briefs(self, *task_ids: str) -> Dict[str, TaskBrief]:
        self._validate_alive()
        ids = set(task_ids)
        result = {}
        fetch = []
        for task_id in ids:
            if task_id in self._fetched_task_briefs:
                result[task_id] = self._fetched_task_briefs[task_id]
            else:
                fetch.append(task_id)
        if fetch:
            tasks = self.container.force_fetch(GoTasks)
            briefs = tasks.get_task_briefs(fetch)
            for task_brief in briefs.values():
                result[task_brief.task_id] = task_brief
                self._fetched_task_briefs[task_brief.task_id] = task_brief
        return result

    def save(self) -> None:
        self._validate_alive()
        self._update_subtasks()
        self._update_state_changes()
        self._do_create_tasks()
        self._do_save_threads()
        self._do_fire_events()
        self._reset()

    def _update_subtasks(self):
        children = self.task.children
        if len(children) == 0:
            return
        tasks = self.get_task_briefs(*children)
        for tid, tb in tasks:
            if TaskState.is_dead(tb.state):
                continue
            children.append(tid)
        self.task.children = children

    def _update_state_changes(self) -> None:
        task = self.task
        task.thread_id = self.thread.id
        task.meta = to_entity_meta(self.ghost)
        state_values = {}
        for name, value in self.state:
            state_values[name] = to_entity_meta(value)
        thread = self.thread
        task.state_values = state_values
        tasks = self.container.force_fetch(GoTasks)
        threads = self.container.force_fetch(GoThreads)
        tasks.save_task(task)
        threads.save_thread(thread)

    def _do_create_tasks(self) -> None:
        tasks = self.container.force_fetch(GoTasks)
        if self._creating_tasks:
            tasks.save_task(*self._creating_tasks.values())
            self._creating_tasks = []

    def _do_save_threads(self) -> None:
        threads = self.container.force_fetch(GoThreads)
        if self._saving_threads:
            threads.save_thread(*self._saving_threads.values())
            self._saving_threads = []

    def _do_fire_events(self) -> None:
        if not self._firing_events:
            return
        bus = self.container.force_fetch(EventBus)
        for e in self._firing_events:
            # all the sub-tasks need notification
            notify = True
            if e.task_id == self.task.parent:
                notify = self.task.depth - 1 == 0
            bus.send_event(e, notify)
        self._firing_events = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            intercepted = self.fail(exc_val)
            self.destroy()
            return intercepted
        else:
            self.save()
            self.destroy()

    def fail(self, err: Optional[Exception]) -> bool:
        if self._failed:
            return True
        self._failed = True
        self.logger.error("Session failed: %s", err)
        if self.upstream is not None:
            message = MessageType.ERROR.new(content=str(err))
            self.upstream.deliver(message)
        return False

    def destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        self.locker.release()
        del self.locker
        self.container.destroy()
        del self.container
        del self._firing_events
        del self.task
        del self.thread
        del self._fetched_task_briefs
        del self.state
        del self.ghost
        del self.ghost_driver
        del self.scope

    def __del__(self):
        self.destroy()
