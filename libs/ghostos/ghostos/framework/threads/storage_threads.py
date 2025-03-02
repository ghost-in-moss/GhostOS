from typing import Optional, Type
from ghostos.core.runtime import GoThreadInfo, GoThreads, ThreadHistory
from ghostos.contracts.workspace import Workspace
from ghostos.contracts.storage import Storage
from ghostos.contracts.logger import LoggerItf
from ghostos_common.helpers import yaml_pretty_dump
from ghostos_container import Provider, Container
import yaml
import os

__all__ = ['GoThreadsByStorage', 'MsgThreadRepoByStorageProvider', 'MsgThreadsRepoByWorkSpaceProvider']


class GoThreadsByStorage(GoThreads):

    def __init__(
            self, *,
            storage: Storage,
            logger: LoggerItf,
            allow_saving_file: bool = True
    ):
        self._storage = storage
        self._logger = logger
        self._allow_saving_file = allow_saving_file

    def get_thread(self, thread_id: str, create: bool = False) -> Optional[GoThreadInfo]:
        path = self._get_thread_filename(thread_id)
        if not self._storage.exists(path):
            if create:
                thread = GoThreadInfo(id=thread_id)
                self.save_thread(thread)
                return thread
            return None
        content = self._storage.get(path)
        data = yaml.safe_load(content)
        thread = GoThreadInfo(**data)
        return thread

    def save_thread(self, thread: GoThreadInfo) -> None:
        data = thread.model_dump(exclude_defaults=True)
        data_content = yaml_pretty_dump(data)
        path = self._get_thread_filename(thread.id)
        saving = data_content.encode('utf-8')
        self._storage.put(path, saving)

    @staticmethod
    def _get_thread_filename(thread_id: str) -> str:
        return thread_id + ".thread.yml"

    def fork_thread(self, thread: GoThreadInfo) -> GoThreadInfo:
        fork = thread.fork()
        self.save_thread(fork)
        return fork


class MsgThreadRepoByStorageProvider(Provider[GoThreads]):

    def __init__(self, threads_dir: str = "runtime/threads"):
        self._threads_dir = threads_dir

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[GoThreads]:
        return GoThreads

    def factory(self, con: Container) -> Optional[GoThreads]:
        storage = con.force_fetch(Storage)
        threads_storage = storage.sub_storage(self._threads_dir)
        logger = con.force_fetch(LoggerItf)
        return GoThreadsByStorage(storage=threads_storage, logger=logger)


class MsgThreadsRepoByWorkSpaceProvider(Provider[GoThreads]):

    def __init__(self, namespace: str = "threads"):
        self._namespace = namespace

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[GoThreads]:
        return GoThreads

    def factory(self, con: Container) -> Optional[GoThreads]:
        workspace = con.force_fetch(Workspace)
        logger = con.force_fetch(LoggerItf)
        threads_storage = workspace.runtime().sub_storage(self._namespace)
        return GoThreadsByStorage(storage=threads_storage, logger=logger)
