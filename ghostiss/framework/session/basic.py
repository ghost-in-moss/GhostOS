from typing import Optional, Callable, List, Iterable
from abc import ABC, abstractmethod
from ghostiss.core.messages import MessageKind, Role, Stream, MessageTypeParser, DefaultMessageTypes
from ghostiss.core.session import (
    Session,
    Process, Processes,
    MsgThread, Threads,
    Task, Tasks, TaskPayload, TaskState,
    Messenger,
    Event, EventBus, DefaultEventType,
)
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


class BasicSession(Session, ABC):

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
        self._eventbus: EventBus = eventbus

    def id(self) -> str:
        return self._task.session_id

    def alive(self) -> bool:
        return not self._upstream.stopped() and self._task.lock is not None and self._timeleft.left() >= 0

    def with_ghost(self, name: str, role: str = Role.ASSISTANT.value) -> "Session":
        self._ghost_name = name
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

    def messenger(self) -> "Messenger":
        payload = TaskPayload.from_task(self._task)
        messenger = DefaultMessenger(
            upstream=self._upstream,
            thread=self._thread,
            name=self._ghost_name,
            payloads=[payload],
            role=self._message_role,
            logger=self._logger,
        )
        return messenger

    def send_messages(self, *messages: MessageKind, role: str = Role.ASSISTANT.value) -> None:
        parser = MessageTypeParser(self._message_role)
        outputs = parser.parse(messages)
        messenger = self.messenger()
        messenger.send(outputs)
        messenger.flush()

    def update_task(self, task: "Task", thread: Optional["MsgThread"] = None) -> None:
        self._task = task
        if thread is not None:
            self._task.thread_id = thread.id
            self._thread = thread

    def update_thread(self, thread: "MsgThread") -> None:
        self._thread = thread

    def fire_events(self, *events: "Event") -> None:
        self._firing_events.extend(list(events))

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

    def cancel_tasks(self, *task_ids: str) -> None:
        self._canceling.extend(list(task_ids))

    def finish(self) -> None:
        if not self.alive():
            raise RuntimeError("Session is not alive")
        with self._eventbus.transaction():
            with self._tasks.transaction():
                with self._threads.transaction():
                    with self._processes.transaction():
                        self._finish_events()
                        self._finish_task_and_thread()
                        self._processes.save_process(process=self._process)

    def _finish_events(self) -> None:
        if not self._firing_events:
            return
        process = self._process
        bus = self._eventbus
        main_task_id = process.main_task_id
        for e in self._firing_events:
            # 异步进程需要通知.
            notify = process.asynchronous or e.task_id != main_task_id
            bus.send_event(e, notify)

    def _finish_task_and_thread(self) -> None:
        self._task.thread_id = self._thread.id
        task = self._task
        # 回收掉完成的任务.
        if task.children and task.too_much_children():
            children = list(self._tasks.get_task_briefs(task.children))
            idx = 0
            max_idx = len(children) - 1
            while task.too_much_children() and idx < max_idx:
                idx += 1
                child = children[idx]
                if child.is_overdue() or TaskState.is_dead(child.task_state):
                    task.remove_child(child.task_id)
        task.update_turn()
        self._tasks.save_task(task)
        self._threads.save_thread(self._thread)

    def fail(self, err: Optional[Exception]) -> None:
        # 暂时只做解开锁.
        locked = self._task.lock
        if locked:
            self._tasks.unlock_task(self._task.task_id, locked)
        self._logger.error(err)

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
        processes.save_process(process)

        task = Task.new(
            task_id=process.main_task_id, session_id=session_id, process_id=process_id,
            name="", description="", meta=EntityMeta(),
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
