from typing import Type, Optional
from ghostos.contracts.configs import Configs, C
from ghostos.contracts.storage import Storage
from ghostos.container import Provider, Container
from ghostos.core.ghosts import Workspace


class StorageConfigs(Configs):
    """
    A Configs(repository) based on Storage, no matter what the Storage is.
    """

    def __init__(self, storage: Storage, conf_dir: str):
        self._storage = storage.sub_storage(conf_dir)

    def get(self, conf_type: Type[C], relative_path: Optional[str] = None) -> C:
        path = conf_type.conf_path()
        relative_path = relative_path if relative_path else path
        content = self._storage.get(relative_path)
        return conf_type.load(content)


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
