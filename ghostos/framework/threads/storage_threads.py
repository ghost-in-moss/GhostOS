from typing import Optional, Type
from ghostos.core.session import MsgThread
from ghostos.core.session.threads import Threads
from ghostos.contracts.storage import Storage
from ghostos.contracts.logger import LoggerItf
from ghostos.helpers import yaml_pretty_dump
from ghostos.container import Provider, Container
import yaml

__all__ = ['StorageThreads', 'StorageThreadsProvider']


class StorageThreads(Threads):

    def __init__(
            self, *,
            storage: Storage,
            logger: LoggerItf
    ):
        self._storage = storage
        self._logger = logger

    def get_thread(self, thread_id: str, create: bool = False) -> Optional[MsgThread]:
        path = self._get_thread_filename(thread_id)
        if not self._storage.exists(path):
            return None
        content = self._storage.get(path)
        data = yaml.safe_load(content)
        thread = MsgThread(**data)
        return thread

    def save_thread(self, thread: MsgThread) -> None:
        data = thread.model_dump(exclude_defaults=True)
        data_content = yaml_pretty_dump(data)
        path = self._get_thread_filename(thread.id)
        saving = data_content.encode('utf-8')
        self._storage.put(path, saving)

    @staticmethod
    def _get_thread_filename(thread_id: str) -> str:
        return thread_id + ".thread.yml"

    def fork_thread(self, thread: MsgThread) -> MsgThread:
        return thread.fork()


class StorageThreadsProvider(Provider[Threads]):

    def __init__(self, threads_dir: str = "runtime/threads"):
        self._threads_dir = threads_dir

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Threads]:
        return Threads

    def factory(self, con: Container) -> Optional[Threads]:
        storage = con.force_fetch(Storage)
        threads_storage = storage.sub_storage(self._threads_dir)
        logger = con.force_fetch(LoggerItf)
        return StorageThreads(storage=threads_storage, logger=logger)
