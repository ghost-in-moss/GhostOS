from typing import Optional, List, Iterable, Dict, Type
import yaml
from ghostos.core.session import TaskState, TaskBrief, Task, Tasks
from ghostos.core.ghosts import Workspace
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.storage import Storage
from ghostos.container import Provider, Container
from ghostos.helpers import uuid

__all__ = ['StorageTasksImpl', 'StorageTasksImplProvider', 'WorkspaceTasksProvider']


class StorageTasksImpl(Tasks):

    def __init__(self, storage: Storage, logger: LoggerItf):
        self._storage = storage
        self._logger = logger
        self._locks: Dict[str, str] = {}

    def save_task(self, *tasks: Task) -> None:
        for task in tasks:
            filename = self._get_task_filename(task.task_id)
            content = yaml.safe_dump(task.model_dump(exclude_defaults=True))
            # todo: 正确的做法要先 check lock.
            self._storage.put(filename, content.encode('utf-8'))

    @staticmethod
    def _get_task_filename(task_id: str) -> str:
        return f"{task_id}.task.yml"

    def _get_task(self, task_id: str) -> Optional[Task]:
        filename = self._get_task_filename(task_id)
        if not self._storage.exists(filename):
            return None
        content = self._storage.get(filename)
        data = yaml.safe_load(content)
        task = Task(**data)
        return task

    def get_task(self, task_id: str, lock: bool) -> Optional[Task]:
        task = self._get_task(task_id)
        if task is None:
            return None
        if lock:
            if task.lock:
                return None
            task.lock = uuid()
            self.save_task(task)
            return task
        else:
            task.lock = None
            return task

    def get_tasks(self, task_ids: List[str], states: Optional[List[TaskState]] = None) -> Iterable[Task]:
        states = set(states) if states else None
        for task_id in task_ids:
            task = self.get_task(task_id, lock=False)
            if states and task.state not in states:
                continue
            yield task

    def get_task_briefs(self, task_ids: List[str], states: Optional[List[TaskState]] = None) -> Iterable[TaskBrief]:
        for task in self.get_tasks(task_ids, states):
            yield TaskBrief.from_task(task)

    def unlock_task(self, task_id: str, lock: str) -> None:
        task = self._get_task(task_id)
        if task is None:
            return
        if task.lock == lock:
            task.lock = None
            self.save_task(task)

    def refresh_task_lock(self, task_id: str, lock: str) -> Optional[str]:
        task = self._get_task(task_id)
        if task is None:
            return uuid()
        if task.lock or task.lock == lock:
            lock = uuid()
            task.lock = lock
            self.save_task(task)
            return lock
        return None


class StorageTasksImplProvider(Provider[Tasks]):
    """
    provide storage based Tasks
    """

    def __init__(self, tasks_dir: str = "runtime/tasks"):
        self.tasks_dir = tasks_dir

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Tasks]:
        return Tasks

    def factory(self, con: Container) -> Optional[Tasks]:
        logger = con.force_fetch(LoggerItf)
        storage = con.force_fetch(Storage)
        tasks_storage = storage.sub_storage(self.tasks_dir)
        return StorageTasksImpl(tasks_storage, logger)


class WorkspaceTasksProvider(Provider[Tasks]):

    def __init__(self, namespace: str = "tasks"):
        self.namespace = namespace

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Tasks]:
        return Tasks

    def factory(self, con: Container) -> Optional[Tasks]:
        workspace = con.force_fetch(Workspace)
        runtime_storage = workspace.runtime()
        tasks_storage = runtime_storage.sub_storage(self.namespace)
        logger = con.force_fetch(LoggerItf)
        return StorageTasksImpl(tasks_storage, logger)
