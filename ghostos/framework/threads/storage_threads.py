from typing import Optional, Type
from os.path import join
from ghostos.core.session import MsgThread
from ghostos.core.session.threads import Threads
from ghostos.contracts.storage import Storage
from ghostos.helpers import yaml_pretty_dump
from ghostos.container import Provider, Container
import yaml


class StorageThreads(Threads):

    def __init__(
            self, *,
            storage: Storage,
            threads_dir: str,
            namespace: str = "",
    ):
        self._storage = storage
        self._threads_dir = threads_dir
        self._namespace = namespace

    def with_namespace(self, namespace: str) -> "Threads":
        return StorageThreads(
            storage=self._storage,
            threads_dir=self._threads_dir,
            namespace=namespace,
        )

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
        if thread.path:
            filepath = self._get_thread_defined_path_filename(thread.path)
            self._storage.put(filepath, saving)

    def _get_thread_filename(self, thread_id: str) -> str:
        dir_ = self._threads_dir
        if self._namespace:
            dir_ = join(dir_, self._namespace)
        filename = thread_id + ".thread.yaml"
        filepath = join(dir_, filename)
        return filepath

    def _get_thread_defined_path_filename(self, path: str) -> str:
        return path + ".thread.yaml"

    def fork_thread(self, thread: MsgThread) -> MsgThread:
        raise NotImplementedError()


class StorageThreadsProvider(Provider[Threads]):

    def __init__(self, thread_dir: str = "runtime/threads"):
        self._thread_dir = thread_dir

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Threads]:
        return Threads

    def factory(self, con: Container) -> Optional[Threads]:
        storage = con.force_fetch(Storage)
        return StorageThreads(storage=storage, threads_dir=self._thread_dir)
