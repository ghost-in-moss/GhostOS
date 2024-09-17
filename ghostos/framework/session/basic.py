from typing import Optional, Callable, List, Iterable, Dict
from ghostos.core.messages import (
    MessageKind, Role, Stream, MessageKindParser, DefaultMessageTypes,
    Buffer, Payload, Attachment,
)
from ghostos.core.session import (
    Session,
    Process, Processes,
    MsgThread, Threads,
    Task, Tasks, TaskPayload, TaskState,
    Messenger,
    Event, EventBus, DefaultEventType,
    TaskBrief,
)
from ghostos.core.llms import FunctionalToken
from ghostos.framework.messengers import DefaultMessenger
from ghostos.helpers import Timeleft, uuid
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.pool import Pool
from ghostos.container import Container
from ghostos.entity import EntityMeta


class Future:
    def __init__(self, future_id: str, bus: EventBus, event: Event):
        self.bus = bus
        self.event = event
        self.future_id = future_id

    def run(self, callback: Callable[[], Iterable[MessageKind]]) -> None:
        messages = list(callback())
        if len(messages) > 0:
            self.event.messages = messages
            self.bus.send_event(self.event, notify=True)
        del self.bus
        del self.event


class BasicSession(Session):

    def __init__(
            self, *,
            ghost_name: str,
            ghost_role: str,
            upstream: Stream,
            eventbus: EventBus,
            pool: Pool,
            processes: Processes,
            tasks: Tasks,
            threads: Threads,
            logger: LoggerItf,
            # 当前任务信息.
            process: Process,
            task: Task,
            thread: MsgThread,
    ):
        self._pool = pool
        self._upstream = upstream
        self._logger = logger
        self._tasks: Tasks = tasks
        self._processes: Processes = processes
        self._ghost_name: str = ghost_name
        self._message_role: str = ghost_role
        self._threads: Threads = threads
        self._eventbus: EventBus = eventbus
        # 需要管理的状态.
        self._task: Task = task
        self._process: Process = process
        self._creating: List[Task] = []
        self._thread: MsgThread = thread
        self._firing_events: List[Event] = []
        self._fetched_task_briefs: Dict[str, TaskBrief] = {}

    def id(self) -> str:
        return self._task.session_id

    def alive(self) -> bool:
        return (
                not self._upstream.stopped()
                and self._task.lock is not None
        )

    def refresh_lock(self) -> bool:
        lock = self._task.lock if self._task.lock else ""
        lock = self._tasks.refresh_task_lock(self._task.task_id, lock)
        if lock:
            self._task.lock = lock
            return True
        return False

    def process(self) -> "Process":
        return self._process

    def task(self) -> "Task":
        return self._task

    def thread(self) -> "MsgThread":
        return self._thread

    def messenger(
            self, *,
            sending: bool = True,
            saving: bool = True,
            thread: Optional[MsgThread] = None,
            name: Optional[str] = None,
            buffer: Optional[Buffer] = None,
            payloads: Optional[Iterable[Payload]] = None,
            attachments: Optional[Iterable[Attachment]] = None,
            functional_tokens: Optional[Iterable[FunctionalToken]] = None
    ) -> "Messenger":
        payload = TaskPayload.from_task(self._task)
        if payloads is None:
            payloads = []
        payloads.append(payload)
        name = name if name else self._assistant_name()
        thread = thread if thread else self._thread

        messenger = DefaultMessenger(
            upstream=self._upstream,
            saving=saving,
            thread=thread,
            buffer=buffer,
            name=name,
            payloads=payloads,
            attachments=attachments,
            role=self._message_role,
            logger=self._logger,
            functional_tokens=functional_tokens,
        )
        return messenger

    def _assistant_name(self) -> str:
        if self._task.assistant:
            return self._task.assistant.name
        return self._ghost_name

    def send_messages(self, *messages: MessageKind, role: str = Role.ASSISTANT.value) -> None:
        parser = MessageKindParser(self._message_role)
        outputs = parser.parse(messages)
        messenger = self.messenger()
        messenger.send(outputs)
        messenger.flush()

    def update_task(self, task: "Task", thread: Optional["MsgThread"], update_history: bool) -> None:
        self._task = task
        if thread is not None:
            self._task.thread_id = thread.id
            self._thread = thread.update_history()
        if update_history:
            self._thread = self._thread.update_history()

    def update_thread(self, thread: "MsgThread", update_history: bool) -> None:
        if update_history:
            thread = thread.update_history()
        self._thread = thread

    def create_tasks(self, *tasks: "Task") -> None:
        self._creating.extend(tasks)

    def fire_events(self, *events: "Event") -> None:
        extending = []
        from_task_name = self._task.name
        from_task_id = self._task.task_id
        for e in events:
            if e.task_id == self._task.parent:
                e.callback = True
            e.from_task_id = from_task_id
            e.from_task_name = from_task_name
            extending.append(e)
        self._firing_events.extend(extending)

    def future(self, name: str, call: Callable[[], Iterable[MessageKind]], reason: str) -> None:
        future_id = uuid()
        # 增加一个消息.
        system = DefaultMessageTypes.DEFAULT.new_system(
            content=f"async call `{name}` with id `{future_id}`, wait for future callback.",
        )
        self.send_messages(system)
        event = DefaultEventType.OBSERVE.new(
            task_id=self._task.task_id,
            from_task_id=self._task.task_id,
            messages=[],
        )
        # 让异步任务全局执行.
        future = Future(future_id, self._eventbus, event)
        self._pool.submit(future.run)

    def _do_quit(self) -> None:
        main_task_id = self._process.main_task_id
        task = self._tasks.get_task(main_task_id, False)
        self._firing_events = []
        for task_id in task.children:
            event = DefaultEventType.KILLING.new(
                task_id=task_id,
                messages=[],
                from_task_id=self._task.task_id,
                reason="the process is quited"
            )
            self._firing_events.append(event)
        self._do_fire_events()

    def _do_create_tasks(self) -> None:
        if self._creating:
            self._tasks.save_task(*self._creating)
            self._creating = []

    def _do_fire_events(self) -> None:
        if not self._firing_events:
            return
        process = self._process
        bus = self._eventbus
        main_task_id = process.main_task_id
        for e in self._firing_events:
            # 异步进程需要通知.
            notify = not self._upstream.is_streaming() or e.task_id != main_task_id
            bus.send_event(e, notify)
        self._firing_events = []

    def _do_finish_task_and_thread(self) -> None:
        self._task.thread_id = self._thread.id
        task = self._task
        # 回收掉完成的任务.
        if task.children and task.too_much_children():
            children = self.get_task_briefs(children=True)
            idx = 0
            max_idx = len(children) - 1
            while task.too_much_children() and idx < max_idx:
                idx += 1
                child = children[idx]
                if child.is_overdue() or TaskState.is_dead(child.task_state):
                    task.remove_child(child.task_id)
        task.update_turn()
        self._task = task
        self._fetched_task_briefs = {}
        self._thread = self._thread.update_history()
        self._tasks.save_task(task)
        self._threads.save_thread(self._thread)

    def get_task_briefs(self, *task_ids, children: bool = False) -> "List[TaskBrief]":
        ids = set(task_ids)
        result = []
        if children:
            for task_id in self._task.children:
                ids.add(task_id)
        if not ids:
            return result

        fetch = []
        for task_id in ids:
            if task_id in self._fetched_task_briefs:
                result.append(self._fetched_task_briefs[task_id])
            else:
                fetch.append(task_id)
        if fetch:
            briefs = self._tasks.get_task_briefs(fetch)
            for task_brief in briefs:
                result.append(task_brief)
                self._fetched_task_briefs[task_brief.task_id] = task_brief
        return result

    def tasks(self) -> Tasks:
        return self._tasks

    def processes(self) -> Processes:
        return self._processes

    def threads(self) -> Threads:
        return self._threads

    def eventbus(self) -> EventBus:
        return self._eventbus

    def update_process(self, process: "Process") -> None:
        self._process = process

    def quit(self) -> None:
        if self._process.main_task_id != self._task.task_id:
            raise RuntimeError(
                f"only main task {self._process.main_task_id} is able to quit process, not {self._task.task_id}"
            )
        self._process.quited = True

    def destroy(self) -> None:
        del self._upstream
        del self._logger
        del self._task
        del self._tasks
        del self._thread
        del self._threads
        del self._process
        del self._processes
        del self._firing_events
        del self._fetched_task_briefs
        del self._pool

    def save(self) -> None:
        with self._eventbus.transaction():
            with self._tasks.transaction():
                with self._threads.transaction():
                    with self._processes.transaction():
                        if self._process.quited:
                            self._do_quit()
                        else:
                            self._do_create_tasks()
                            self._do_finish_task_and_thread()
                            self._do_fire_events()
                            if self._process.main_task_id == self._task.task_id:
                                self._processes.save_process(process=self._process)

    def fail(self, err: Optional[Exception]) -> None:
        # 暂时只做解开锁.
        locked = self._task.lock
        if locked:
            self._tasks.unlock_task(self._task.task_id, locked)
            self._task.lock = None
        self._upstream.deliver(DefaultMessageTypes.ERROR.new(content=str(err)))
        self._logger.error(err)

    def done(self) -> None:
        locked = self._task.lock
        if locked:
            self._tasks.unlock_task(self._task.task_id, locked)
        self._upstream.deliver(DefaultMessageTypes.final())
