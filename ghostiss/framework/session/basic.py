from typing import Optional, Callable, List, Iterable, Dict
from ghostiss.core.messages import (
    MessageKind, Role, Stream, MessageKindParser, DefaultMessageTypes,
    Buffer, Payload, Attachment,
)
from ghostiss.core.session import (
    Session,
    Process, Processes,
    MsgThread, Threads,
    Task, Tasks, TaskPayload, TaskState,
    Messenger,
    Event, EventBus, DefaultEventType,
    TaskBrief,
)
from ghostiss.core.llms import FunctionalToken
from ghostiss.framework.messengers import DefaultMessenger
from ghostiss.helpers import Timeleft, uuid
from ghostiss.contracts.logger import LoggerItf
from ghostiss.contracts.pool import Pool
from ghostiss.container import Container
from ghostiss.entity import EntityMeta


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
            upstream: Stream,
            eventbus: EventBus,
            pool: Pool,
            tasks: Tasks,
            threads: Threads,
            processes: Processes,
            logger: LoggerItf,
            # 当前任务信息.
            process: Process,
            task: Task,
            thread: MsgThread,
            timeout: float = 0.0,
    ):
        self._pool = pool
        self._upstream = upstream
        self._logger = logger
        self._task: Task = task
        self._tasks: Tasks = tasks
        self._process: Process = process
        self._processes: Processes = processes
        self._ghost_name: str = ""
        self._message_role: str = Role.ASSISTANT.value
        self._thread: MsgThread = thread
        self._threads: Threads = threads
        self._timeleft: Timeleft = Timeleft(timeout)
        self._firing_events: List[Event] = []
        self._canceling: List[str] = []
        self._killing: List[str] = []
        self._creating: List[Task] = []
        self._eventbus: EventBus = eventbus
        self._fetched_task_briefs: Dict[str, TaskBrief] = {}

    def id(self) -> str:
        return self._task.session_id

    def alive(self) -> bool:
        return (
                not self._upstream.stopped()
                and self._task.lock is not None
                and self._timeleft.left() >= 0
        )

    def with_ghost(
            self,
            name: str,
            role: str = Role.ASSISTANT.value,
            logger: Optional[LoggerItf] = None,
    ) -> "Session":
        self._ghost_name = name
        self._message_role = role
        if logger is not None:
            self._logger = logger
        return self

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
        name = name if name else self._ghost_name
        thread = thread if thread else self._thread

        messenger = DefaultMessenger(
            upstream=self._upstream,
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
        event = DefaultEventType.THINK.new(
            task_id=self._task.task_id,
            from_task_id=self._task.task_id,
            messages=[],
        )
        # 让异步任务全局执行.
        future = Future(future_id, self._eventbus, event)
        self._pool.submit(future.run)

    def done(self) -> None:
        if not self.alive():
            raise RuntimeError("Session is not alive")
        with self._eventbus.transaction():
            with self._tasks.transaction():
                with self._threads.transaction():
                    with self._processes.transaction():
                        if self._process.quited:
                            self._do_quit()
                        else:
                            self._do_create_tasks()
                            self._do_finish_task_and_thread()
                            self._processes.save_process(process=self._process)
                            self._do_fire_events()
                        self._upstream.deliver(DefaultMessageTypes.final())

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

    def fail(self, err: Optional[Exception]) -> None:
        # 暂时只做解开锁.
        locked = self._task.lock
        if locked:
            self._tasks.unlock_task(self._task.task_id, locked)
        self._upstream.deliver(DefaultMessageTypes.ERROR.new(content=str(err)))
        self._logger.error(err)

    def update_process(self, process: "Process") -> None:
        self._process = process

    def quit(self) -> None:
        if self._process.main_task_id != self._task.task_id:
            raise RuntimeError(
                f"only main task {self._process.main_task_id} is able to quit process, not {self._task.task_id}"
            )
        self._process.quited = True
        # todo: 要做的事情: 1. 标记 quited 并保存. 2. 从根节点开始, 通知所有的任务取消.

    def destroy(self) -> None:
        del self._pool
        del self._upstream
        del self._logger
        del self._task
        del self._tasks
        del self._thread
        del self._threads
        del self._process
        del self._processes
        del self._firing_events
        del self._canceling
        del self._fetched_task_briefs

    @classmethod
    def create_session(
            cls, *,
            container: Container,
            ghost_meta: EntityMeta,
            upstream: Stream,
            session_id: str,
            is_async: bool,
            task_id: Optional[str] = None,
    ) -> Session:
        process_id = task_id if task_id else uuid()
        process = Process.new(session_id=session_id, is_async=is_async, process_id=process_id, ghost_meta=ghost_meta)
        processes = container.force_fetch(Processes)
        tasks = container.force_fetch(Tasks).with_namespace(process_id)
        task = Task.new(
            task_id=process.main_task_id, session_id=session_id, process_id=process_id,
            name="", description="", meta=EntityMeta(type="", data={}),
        )
        tasks.save_task(task)
        threads = container.force_fetch(Threads).with_namespace(process_id)
        thread = threads.get_thread(task.thread_id, create=True)

        eventbus = container.force_fetch(EventBus).with_namespace(process_id)
        pool = container.force_fetch(Pool)
        logger = container.force_fetch(LoggerItf)

        # 初始化创建.
        processes.save_process(process)
        threads.save_thread(thread)
        return cls(
            upstream=upstream,
            eventbus=eventbus,
            pool=pool,
            logger=logger,
            task=task,
            tasks=tasks,
            process=process,
            processes=processes,
            thread=thread,
            threads=threads,
        )

    @classmethod
    def find_session(
            cls,
            container: Container,
            upstream: Stream,
            session_id: str,
            task_id: Optional[str] = None,
            task: Optional[Task] = None,
    ) -> Optional[Session]:
        tasks = container.force_fetch(Tasks)
        if task is None and task_id is not None:
            task = tasks.get_task(task_id, lock=True)
            if task is None:
                # task 不存在.
                return None
            elif task.session_id != session_id:
                # 不合法的查询.
                return None

        processes = container.force_fetch(Processes)
        p = processes.get_session_process(session_id)
        if p is None:
            # 进程不存在.
            return None

        if task is None:
            # 没有传入 task.
            task_id = p.main_task_id
            task = tasks.get_task(task_id, lock=True)

        if task is None or task.lock is None:
            # 没有锁定成功.
            return None

        threads = container.force_fetch(Threads)
        thread = threads.get_thread(task.thread_id, create=True)
        if thread is None:
            raise RuntimeError(f"No thread {task.thread_id} found for task {task.task_id} and fail to create one")

        pool = container.force_fetch(Pool)
        logger = container.force_fetch(LoggerItf)
        eventbus = container.force_fetch(EventBus)

        return cls(
            upstream=upstream,
            eventbus=eventbus,
            pool=pool,
            logger=logger,
            task=task,
            tasks=tasks,
            process=p,
            processes=processes,
            thread=thread,
            threads=threads,
        )
