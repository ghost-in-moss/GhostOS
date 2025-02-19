from typing import Optional, Dict, Type
import yaml
from ghostos.core.runtime import GoProcess
from ghostos.core.runtime.processes import GoProcesses
from ghostos.contracts.storage import Storage
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.workspace import Workspace
from ghostos_container import Provider, Container
from ghostos_common.helpers import yaml_pretty_dump

__all__ = ['StorageGoProcessesImpl', 'StorageProcessImplProvider', 'WorkspaceProcessesProvider']


class StorageGoProcessesImpl(GoProcesses):
    session_map_name = "sessions.yml"

    def __init__(self, storage: Storage, logger: LoggerItf):
        self._storage = storage
        self._logger = logger

    def _get_session_process_map(self) -> Dict[str, str]:
        filename = self.session_map_name
        if self._storage.exists(filename):
            content = self._storage.get(filename)
            data = yaml.safe_load(content)
            return data
        return {}

    @staticmethod
    def _get_process_filename(shell_id: str) -> str:
        return f"{shell_id}.process.yml"

    def get_process(self, shell_id: str) -> Optional[GoProcess]:
        filename = self._get_process_filename(shell_id)
        if not self._storage.exists(filename):
            return None
        content = self._storage.get(filename)
        data = yaml.safe_load(content)
        process = GoProcess(**data)
        return process

    def save_process(self, process: GoProcess) -> None:
        filename = self._get_process_filename(process.shell_id)
        data = process.model_dump(exclude_defaults=True)
        content = yaml_pretty_dump(data)
        self._storage.put(filename, content.encode())


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
