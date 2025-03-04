from typing import Optional, List, Iterable, Tuple, TypeVar, Dict, Union, Any, Callable
from ghostos.errors import StreamingError
from ghostos.abcd import (
    Session, Ghost, GhostDriver, Matrix, Scope, Mindflow, Operator, Subtasks,
    Messenger,
)
from ghostos.abcd import get_ghost_driver
from ghostos.core.messages import (
    MessageKind, Message, FunctionCaller, Stream, Role, MessageKindParser, MessageType,
    Payload
)
from ghostos.core.messages.message_classes import (
    FunctionCallMessage,
    ConfirmMessage,
)
from ghostos.core.runtime import (
    TaskBrief, GoTaskStruct, TaskPayload, GoTasks, TaskState,
    EventBus, Event, EventTypes,
    GoThreads,
    GoThreadInfo,
)
from ghostos_common.prompter import PromptObjectModel
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.variables import Variables
from ghostos_container import Container, provide, Contracts
from ghostos_common.entity import to_entity_meta, from_entity_meta, get_entity, EntityType
from ghostos_common.identifier import get_identifier
from ghostos.framework.messengers import DefaultMessenger
from ghostos.framework.ghostos.mindflow_impl import MindflowImpl
from ghostos.framework.ghostos.subtasks_impl import SubtasksImpl
from threading import Lock

from ghostos.errors import SessionError

G = TypeVar("G", bound=Ghost)


class EmptyOperator(Operator):

    def run(self, session: Session) -> Union[Operator, None]:
        return None

    def destroy(self):
        pass


class SessionImpl(Session[Ghost]):
    contracts = Contracts([
        GoThreads,
        GoTasks,
        EventBus,
    ])

    def __init__(
            self,
            container: Container,
            logger: LoggerItf,
            scope: Scope,
            stream: Optional[Stream],
            task: GoTaskStruct,
            refresh_callback: Callable[[], bool],
            alive_check: Callable[[], bool],
            max_errors: int,
            safe_mode: bool = False,
    ):
        # session level container
        self.container = Container(parent=container, name="session")

        self.upstream = stream
        self.task = task
        self.logger = logger
        self._refresh_callback = refresh_callback
        self._alive_check = alive_check
        threads = container.force_fetch(GoThreads)
        thread = threads.get_thread(task.thread_id, create=True)
        self.thread = thread
        self.scope = scope

        self.ghost: G = get_entity(self.task.meta, Ghost)
        self.ghost_driver: GhostDriver[G] = get_ghost_driver(self.ghost)
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
        self._system_logs: List[str] = []
        self._failed = False
        self._done = False
        self._destroyed = False
        self._saved = False
        self._bootstrap()
        self._respond_lock = Lock()
        self._respond_buffer: List = []
        self._safe_mode = safe_mode

        Session.instance_count += 1

    def __del__(self):
        # for gc test
        Session.instance_count -= 1
        self.destroy()

    def _bootstrap(self):
        self.contracts.validate(self.container)
        self.container.set(Session, self)
        self.container.set(Scope, self.scope)
        self.container.set(MessageKindParser, self._message_parser)
        self.container.register(provide(GoTaskStruct, False)(lambda c: self.task))
        self.container.register(provide(GoThreadInfo, False)(lambda c: self.thread))
        self.container.register(provide(Mindflow, False)(lambda c: self.mindflow()))
        self.container.register(provide(Subtasks, False)(lambda c: self.subtasks()))
        self.container.register(provide(Messenger, False)(lambda c: self.messenger()))

        # register session level providers.
        providers = self.ghost_driver.providers()
        for provider in providers:
            self.container.register(provider)
        self.container.bootstrap()
        # truncate thread.

    def get_truncated_thread(self) -> GoThreadInfo:
        thread = self.ghost_driver.truncate(self)
        return thread

    @staticmethod
    def unmarshal_state(task: GoTaskStruct) -> Dict[str, EntityType]:
        state_values = {}
        for key, entity_meta in task.state_values.items():
            entity = from_entity_meta(entity_meta)
            state_values[key] = entity
        return state_values

    def alive(self) -> bool:
        if self._failed or self._destroyed:
            return False
        return self._alive_check() and (self.upstream is None or self.upstream.alive())

    def allow_streaming(self) -> bool:
        return self.upstream.allow_streaming() if self.upstream else False

    def _validate_alive(self):
        if not self.alive():
            raise RuntimeError(f"Session is not alive")

    def to_messages(self, values: Iterable[Union[MessageKind, Any]]) -> List[Message]:
        return list(self._message_parser.parse(values))

    def parse_event(self, event: Event) -> Tuple[Optional[Event], Optional[Operator]]:
        # todo: add logs
        self.logger.info("session parse event %s", event.event_id)
        self._validate_alive()
        driver = get_ghost_driver(self.ghost)

        # if the task is new, initialize the task.
        if self.task.state == TaskState.NEW.value:
            self.logger.info("session initialize task %s before event %s", self.task.task_id, event.event_id)
            driver.on_creating(self)
            self.task.state = TaskState.RUNNING.value

        # approve pending callers
        if EventTypes.APPROVE.value == event.type:
            last_turn = self.thread.last_turn()
            if last_turn.approved:
                self.logger.error("session received approve event %s but already approved", event.event_id)
                return None, None
            elif last_turn.pending_callers:
                last_turn.approved = True
                self.logger.info("session approved last turn %s", last_turn.turn_id)
                op = self.handle_callers(last_turn.pending_callers, True)
                return None, op
            else:
                self.logger.info("session received approved event but no pending callers", event.event_id)
                return None, None

        if EventTypes.ACTION_CALL.value == event.type:
            self.thread.new_turn(event)
            callers = []
            for message in event.messages:
                fc = FunctionCallMessage.from_message(message)
                if fc is None:
                    continue
                callers.append(fc.caller)
            return None, self.handle_callers(callers, True)

        # notification do not trigger the handling
        if EventTypes.NOTIFY.value == event.type:
            self.thread.new_turn(event)
            return None, EmptyOperator()

        if EventTypes.INPUT.value == event.type:
            # only input event can reset errors.
            self.task.errors = 0
            self.task.state = TaskState.RUNNING.value
            if event.context is not None:
                self.task.context = event.context

        # other event
        elif self.task.is_dead():
            # dead task can only respond event from parent input.
            self.thread.new_turn(event)
            self.logger.info(
                "task %s is dead, save event %s without run", self.scope.task_id, event.event_id,
            )
            return None, EmptyOperator()

        if EventTypes.ERROR.value == event.type:
            self.task.errors += 1
            if self.task.errors > self._max_errors:
                # if reach max errors, fail the task
                return None, self.mindflow().fail("task failed too much, exceeds max errors")

        if EventTypes.CANCEL.value == event.type:
            # cancel self and all subtasks.
            self.task.errors = 0
            self.thread.new_turn(event)
            self.task.state = TaskState.CANCELLED.value
            # cancel children.
            if self.task.children:
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

        event.context = None
        return event, None

    def system_log(self, log: str) -> None:
        self._system_logs.append(log)

    def is_safe_mode(self) -> bool:
        return self._safe_mode or self.ghost_driver.is_safe_mode()

    def mindflow(self) -> Mindflow:
        self._validate_alive()
        return MindflowImpl(self, self._message_parser)

    def subtasks(self) -> Subtasks:
        return SubtasksImpl(self)

    def get_context(self) -> Optional[PromptObjectModel]:
        if self.task.context is None:
            return None
        return get_entity(self.task.context, PromptObjectModel)

    def get_artifact(self) -> Ghost.ArtifactType:
        return self.ghost_driver.get_artifact(self)

    def get_system_instructions(self) -> str:
        return self.ghost_driver.get_system_instruction(self)

    def refresh(self, throw: bool = False) -> bool:
        if self._failed:
            if throw:
                raise RuntimeError(f"Session is already failed")
            return False
        if self._destroyed:
            if throw:
                raise RuntimeError(f"Session is already destroyed")
            return False

        if not self.alive():
            if throw:
                raise RuntimeError(f"Session is not alive")
            return False
        if self._refresh_callback():
            self._saved = False
            return True
        elif throw:
            raise RuntimeError(f"session refresh callback failed")
        else:
            return False

    def _reset(self):
        self._fetched_task_briefs = {}
        self._firing_events = []
        self._creating_tasks = {}
        self._saving_threads = {}
        self._system_logs = []
        self._respond_buffer = []
        self.task = self.task.new_turn()

    def messenger(
            self, *,
            name: str = "",
            stage: str = "",
            payloads: Optional[List[Payload]] = None,
    ) -> Messenger:
        self._validate_alive()

        # prepare payloads.
        task_payload = TaskPayload.from_task(self.task)
        if payloads is None:
            payloads = [task_payload]
        else:
            payloads.append(task_payload)

        identity = get_identifier(self.ghost)
        return DefaultMessenger(
            upstream=self.upstream,
            name=name or identity.name,
            role=Role.ASSISTANT.value,
            payloads=payloads,
            stage=str(stage),
            output_pipes=self.ghost_driver.output_pipes()
        )

    def respond(
            self,
            messages: Iterable[MessageKind],
            stage: str = "",
            save: bool = True,
    ) -> Tuple[List[Message], List[FunctionCaller]]:
        self._validate_alive()
        messages = self._message_parser.parse(messages)
        with self._respond_lock:
            messenger = self.messenger(stage=stage)
            try:
                messenger.send(messages)
            except StreamingError as e:
                raise SessionError(f"session failed during streaming: {e}")

            buffer, callers = messenger.flush()
            self.logger.debug("append messages to thread: %s", buffer)
            if save:
                self.thread.append(*buffer)
            return buffer, callers

    def respond_buffer(self, messages: Iterable[MessageKind], stage: str = "") -> None:
        self._validate_alive()
        messages = self._message_parser.parse(messages)
        items = []
        for message in messages:
            if message.is_complete():
                message.stage = stage
                items.append(message)
        self._respond_buffer.extend(items)

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

    def save_threads(self, *threads: GoThreadInfo) -> None:
        self._validate_alive()
        for t in threads:
            self._saving_threads[t.id] = t

    def call(self, ghost: Ghost, ctx: Ghost.ContextType) -> Ghost.ArtifactType:
        self._validate_alive()
        shell = self.container.force_fetch(Matrix)
        return shell.call(ghost, ctx)

    def fire_events(self, *events: "Event") -> None:
        self._validate_alive()
        firing = list(events)
        self.logger.debug("session fire events: %d", len(firing))
        self._firing_events.extend(firing)

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
        if self._saved or self._destroyed:
            return
        try:
            self._saved = True
            self.logger.info("saving session on %s", self.scope.model_dump())
            self._validate_alive()
            self._update_subtasks()
            self._update_state_changes()
            self._do_create_tasks()
            self._do_save_threads()
            self._do_fire_events()
            self._reset()
        except Exception as e:
            self.logger.exception(e)
            raise

    def _update_subtasks(self):
        children = self.task.children
        if len(children) == 0:
            return
        tasks = self.get_task_briefs(*children)
        for tid, tb in tasks:
            if TaskState.is_dead(tb.state_name):
                continue
            children.append(tid)
        self.task.children = children

    def _update_state_changes(self) -> None:
        task = self.task
        thread = self.thread
        task.meta = to_entity_meta(self.ghost)
        state_values = {}
        for name, value in self.state.items():
            state_values[name] = to_entity_meta(value)

        task.thread_id = thread.id
        task.state_values = state_values
        if task.state == TaskState.RUNNING.value:
            task.state = TaskState.WAITING.value

        # update respond buffer
        if len(self._respond_buffer) > 0:
            messenger = self.messenger()
            messenger.send(self._respond_buffer)
            items, callers = messenger.flush()
            thread.append(*items)

        # update system log
        if len(self._system_logs) > 0:
            content = "\n".join(self._system_logs)
            message = Role.SYSTEM.new(content=content)
            thread.append(message)
            self._system_logs = []

        # if current thread is not approved, send message to client side.
        if thread.current and not thread.current.approved:
            confirm = ConfirmMessage.new(
                content="approve",
                visible=False,
                event=EventTypes.APPROVE.new(
                    task_id=task.task_id,
                    messages=[],
                ).model_dump(exclude_defaults=True),
            )
            confirm_msg = confirm.to_message()
            messenger = self.messenger()
            messenger.send([confirm_msg])
            sent, _ = messenger.flush()
            # do not save confirm to thread.
            thread.store()

        tasks = self.container.force_fetch(GoTasks)
        threads = self.container.force_fetch(GoThreads)
        self.logger.debug("task info %s", task.model_dump())
        tasks.save_task(task)
        threads.save_thread(thread)

    def _do_create_tasks(self) -> None:
        tasks = self.container.force_fetch(GoTasks)
        if self._creating_tasks:
            tasks.save_task(*self._creating_tasks.values())
            self._creating_tasks = {}

    def _do_save_threads(self) -> None:
        threads = self.container.force_fetch(GoThreads)
        if self._saving_threads:
            for saving in self._saving_threads.values():
                threads.save_thread(saving)
            self._saving_threads = {}

    def _do_fire_events(self) -> None:
        if not self._firing_events:
            return
        logger = self.logger
        bus = self.container.force_fetch(EventBus)
        for e in self._firing_events:
            # all the sub-tasks need notification
            notify = True
            if e.task_id == self.task.parent:
                notify = self.task.depth - 1 == 0
            bus.send_event(e, notify)
            logger.debug("session fired event %s", {e.event_id})
        self._firing_events = []

    def __enter__(self):
        if not self.refresh(throw=True):
            raise RuntimeError(f"Failed to start session")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug("session exited")
        if exc_val is not None:
            self.logger.exception(exc_val)
            intercepted = self.fail(exc_val)
            self.destroy()
            return intercepted
        elif not self._destroyed:
            self.save()
            self.destroy()
            return None

    def fail(self, err: Optional[Exception]) -> bool:
        if self._failed:
            return False
        self._failed = True
        self.logger.error("Session failed: %s at task %s", err, self.task.task_id)
        if self.upstream is not None and self.upstream.alive():
            message = MessageType.ERROR.new(content=str(err))
            self.upstream.deliver(message)
        return False

    def destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        self.container.shutdown()
        del self._alive_check
        del self.container
        del self._firing_events
        del self.task
        del self.thread
        del self._fetched_task_briefs
        del self.state
        del self.ghost
        del self.ghost_driver
        del self.scope
