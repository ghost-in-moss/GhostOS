from typing import Optional, Dict
from ghostos.contracts.configs import Configs
from ghostos.contracts.storage import Storage
from ghostos_container import Provider, Container
from ghostos.contracts.workspace import Workspace
from .basic import BasicConfigs


class StorageConfigs(BasicConfigs):

    def __init__(self, storage: Storage, conf_dir: str):
        self._storage = storage.sub_storage(conf_dir)

    def _get(self, relative_path: str) -> bytes:
        return self._storage.get(relative_path)

    def _put(self, relative_path: str, content: bytes) -> None:
        self._storage.put(relative_path, content)

    def _exists(self, relative_path: str) -> bool:
        return self._storage.exists(relative_path)


class ConfigsByStorageProvider(Provider[Configs]):

    def __init__(self, conf_dir: str):
        self._conf_dir = conf_dir

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[Configs]:
        storage = con.force_fetch(Storage)
        return StorageConfigs(storage, self._conf_dir)


class WorkspaceConfigsProvider(Provider[Configs]):
    """
    the Configs repository located at storage - workspace.configs()
    """

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[Configs]:
        workspace = con.force_fetch(Workspace)
        return StorageConfigs(workspace.configs(), "")
