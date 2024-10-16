from typing import Optional, Type
from ghostos.core.session import MsgThread, MsgThreadRepo, SimpleMsgThread
from ghostos.core.ghosts import Workspace
from ghostos.contracts.storage import Storage
from ghostos.contracts.logger import LoggerItf
from ghostos.helpers import yaml_pretty_dump
from ghostos.container import Provider, Container
import yaml
import os

__all__ = ['MsgThreadRepoByStorage', 'MsgThreadRepoByStorageProvider', 'MsgThreadsRepoByWorkSpaceProvider']


class MsgThreadRepoByStorage(MsgThreadRepo):

    def __init__(
            self, *,
            storage: Storage,
            logger: LoggerItf,
            allow_saving_file: bool = True
    ):
        self._storage = storage
        self._logger = logger
        self._allow_saving_file = allow_saving_file

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
        # saving to special file
        if thread.save_file and self._allow_saving_file:
            simple = SimpleMsgThread.from_thread(thread)
            simple_data = simple.model_dump(exclude_defaults=True)
            content = yaml_pretty_dump(simple_data)
            if thread.save_file.startswith('/'):
                # saving to absolute path
                saving_dir = os.path.dirname(thread.save_file)
                if not os.path.exists(saving_dir):
                    os.makedirs(saving_dir)
                with open(thread.save_file, 'wb') as f:
                    f.write(content.encode('UTF-8'))
            else:
                # saving to relative path
                self._storage.put(thread.save_file, content.encode('UTF-8'))

    @staticmethod
    def _get_thread_filename(thread_id: str) -> str:
        return thread_id + ".thread.yml"

    def fork_thread(self, thread: MsgThread) -> MsgThread:
        return thread.fork()


class MsgThreadRepoByStorageProvider(Provider[MsgThreadRepo]):

    def __init__(self, threads_dir: str = "runtime/threads"):
        self._threads_dir = threads_dir

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[MsgThreadRepo]:
        return MsgThreadRepo

    def factory(self, con: Container) -> Optional[MsgThreadRepo]:
        storage = con.force_fetch(Storage)
        threads_storage = storage.sub_storage(self._threads_dir)
        logger = con.force_fetch(LoggerItf)
        return MsgThreadRepoByStorage(storage=threads_storage, logger=logger)


class MsgThreadsRepoByWorkSpaceProvider(Provider[MsgThreadRepo]):

    def __init__(self, namespace: str = "threads"):
        self._namespace = namespace

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[MsgThreadRepo]:
        return MsgThreadRepo

    def factory(self, con: Container) -> Optional[MsgThreadRepo]:
        workspace = con.force_fetch(Workspace)
        logger = con.force_fetch(LoggerItf)
        threads_storage = workspace.runtime().sub_storage(self._namespace)
        return MsgThreadRepoByStorage(storage=threads_storage, logger=logger)
