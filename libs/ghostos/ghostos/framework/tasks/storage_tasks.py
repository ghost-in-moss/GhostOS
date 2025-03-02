import time
from typing import Optional, List, Iterable, Type, TypedDict
import yaml
from ghostos.core.runtime import TaskState, TaskBrief, GoTaskStruct, GoTasks
from ghostos.contracts.workspace import Workspace
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.storage import Storage
from ghostos_container import Provider, Container
from ghostos.core.runtime.tasks import TaskLocker
from ghostos_common.helpers import uuid, timestamp

__all__ = ['StorageGoTasksImpl', 'StorageTasksImplProvider', 'WorkspaceTasksProvider']


class SimpleStorageLocker(TaskLocker):
    class LockData(TypedDict):
        lock_id: str
        overdue: float

    def __init__(self, storage: Storage, task_id: str, overdue: float, force: bool = False):
        self.task_id = task_id
        self.storage = storage
        self.lock_id = uuid()
        self._acquired = False
        self._overdue = overdue
        self._force = force

    def acquire(self) -> bool:
        filename = self.locker_file_name()
        if self.storage.exists(filename):
            content = self.storage.get(filename)
            data = None
            if content:
                data = yaml.safe_load(content)
            if data:
                lock = self.LockData(**data)
                now = time.time()
                if lock['lock_id'] == self.lock_id or now - float(lock["overdue"]) > 0:
                    self.create_lock()
                    return True
                elif not self._acquired and self._force:
                    self.create_lock()
                    return True
                else:
                    return False
        self.create_lock()
        return True

    def acquired(self) -> bool:
        return self._acquired

    def create_lock(self) -> None:
        filename = self.locker_file_name()
        overdue_at = time.time() + self._overdue
        lock = self.LockData(lock_id=self.lock_id, overdue=overdue_at)
        content = yaml.safe_dump(lock)
        self.storage.put(filename, content.encode())
        self._acquired = True

    def locker_file_name(self) -> str:
        return f'{self.task_id}.lock'

    def refresh(self) -> bool:
        if not self._acquired:
            return False
        return self.acquire()

    def release(self) -> bool:
        if not self._acquired:
            return False
        filename = self.locker_file_name()
        if self.refresh():
            self.storage.remove(filename)
            self._acquired = False
            return True
        return False


class StorageGoTasksImpl(GoTasks):

    def __init__(self, storage: Storage, logger: LoggerItf):
        self._storage = storage
        self._logger = logger

    def save_task(self, *tasks: GoTaskStruct) -> None:
        for task in tasks:
            filename = self._get_task_filename(task.task_id)
            data = task.model_dump(exclude_defaults=True)
            content = yaml.safe_dump(data)
            task.updated = timestamp()
            self._storage.put(filename, content.encode('utf-8'))

    @staticmethod
    def _get_task_filename(task_id: str) -> str:
        return f"{task_id}.task.yml"

    def _get_task(self, task_id: str) -> Optional[GoTaskStruct]:
        filename = self._get_task_filename(task_id)
        if not self._storage.exists(filename):
            return None
        content = self._storage.get(filename)
        data = yaml.safe_load(content)
        task = GoTaskStruct(**data)
        return task

    def exists(self, task_id: str) -> bool:
        filename = self._get_task_filename(task_id)
        return self._storage.exists(filename)

    def get_task(self, task_id: str) -> Optional[GoTaskStruct]:
        return self._get_task(task_id)

    def get_tasks(self, task_ids: List[str], states: Optional[List[TaskState]] = None) -> Iterable[GoTaskStruct]:
        states = set(states) if states else None
        for task_id in task_ids:
            task = self.get_task(task_id)
            if states and task.state not in states:
                continue
            yield task

    def get_task_briefs(self, task_ids: List[str], states: Optional[List[TaskState]] = None) -> Iterable[TaskBrief]:
        for task in self.get_tasks(task_ids, states):
            yield TaskBrief.from_task(task)

    def lock_task(self, task_id: str, overdue: float = 30, force: bool = False) -> TaskLocker:
        return SimpleStorageLocker(self._storage, task_id, overdue, force)


class StorageTasksImplProvider(Provider[GoTasks]):
    """
    provide storage based Tasks
    """

    def __init__(self, tasks_dir: str = "runtime/tasks"):
        self.tasks_dir = tasks_dir

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[GoTasks]:
        return GoTasks

    def factory(self, con: Container) -> Optional[GoTasks]:
        logger = con.force_fetch(LoggerItf)
        storage = con.force_fetch(Storage)
        tasks_storage = storage.sub_storage(self.tasks_dir)
        return StorageGoTasksImpl(tasks_storage, logger)


class WorkspaceTasksProvider(Provider[GoTasks]):

    def __init__(self, namespace: str = "tasks"):
        self.namespace = namespace

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[GoTasks]:
        return GoTasks

    def factory(self, con: Container) -> Optional[GoTasks]:
        workspace = con.force_fetch(Workspace)
        runtime_storage = workspace.runtime()
        tasks_storage = runtime_storage.sub_storage(self.namespace)
        logger = con.force_fetch(LoggerItf)
        return StorageGoTasksImpl(tasks_storage, logger)
