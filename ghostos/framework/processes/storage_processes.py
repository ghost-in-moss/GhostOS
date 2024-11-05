from typing import Optional, Dict, Type
import yaml
from ghostos.core.session import GoProcess
from ghostos.core.session.processes import GoProcesses
from ghostos.contracts.storage import Storage
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.workspace import Workspace
from threading import Lock
from ghostos.container import Provider, Container

__all__ = ['StorageGoProcessesImpl', 'StorageProcessImplProvider', 'WorkspaceProcessesProvider']


class StorageGoProcessesImpl(GoProcesses):
    session_map_name = "sessions.yml"

    def __init__(self, storage: Storage, logger: LoggerItf):
        self._storage = storage
        self._logger = logger
        self._lock = Lock()

    def _get_session_process_map(self) -> Dict[str, str]:
        filename = self.session_map_name
        if self._storage.exists(filename):
            content = self._storage.get(filename)
            data = yaml.safe_load(content)
            return data
        return {}

    @staticmethod
    def _get_process_filename(process_id: str) -> str:
        return f"{process_id}.process.yml"

    def get_process(self, process_id: str) -> Optional[GoProcess]:
        filename = self._get_process_filename(process_id)
        if self._storage.exists(filename):
            content = self._storage.get(filename)
            data = yaml.safe_load(content)
            process = GoProcess(**data)
            return process
        return None

    def _save_session_process_map(self, session_map: Dict[str, str]) -> None:
        content = yaml.safe_dump(session_map)
        filename = self.session_map_name
        self._storage.put(filename, content.encode("utf-8"))

    def get_session_process(self, session_id: str) -> Optional[GoProcess]:
        m = self._get_session_process_map()
        process_id = m.get(session_id, None)
        if process_id is None:
            return None
        return self.get_process(process_id)

    def save_process(self, process: GoProcess) -> None:
        session_id = process.session_id
        process_id = process.process_id
        with self._lock:
            m = self._get_session_process_map()
            m[session_id] = process_id
            self._save_session_process_map(m)
        content = yaml.safe_dump(process.model_dump(exclude_defaults=True))
        filename = self._get_process_filename(process_id)
        self._storage.put(filename, content.encode("utf-8"))


class StorageProcessImplProvider(Provider[GoProcesses]):
    def __init__(self, process_dir: str = "runtime/processes"):
        self.process_dir = process_dir

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[GoProcesses]:
        return GoProcesses

    def factory(self, con: Container) -> Optional[GoProcesses]:
        storage = con.force_fetch(Storage)
        logger = con.force_fetch(LoggerItf)
        processes_storage = storage.sub_storage(self.process_dir)
        return StorageGoProcessesImpl(processes_storage, logger)


class WorkspaceProcessesProvider(Provider[GoProcesses]):
    def __init__(self, process_dir: str = "processes"):
        self.process_dir = process_dir

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[GoProcesses]:
        return GoProcesses

    def factory(self, con: Container) -> Optional[GoProcesses]:
        workspace = con.force_fetch(Workspace)
        logger = con.force_fetch(LoggerItf)
        processes_storage = workspace.runtime().sub_storage(self.process_dir)
        return StorageGoProcessesImpl(processes_storage, logger)
