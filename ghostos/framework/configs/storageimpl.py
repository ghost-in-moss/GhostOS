from typing import Type, Optional
from ghostos.contracts.configs import Configs, C
from ghostos.contracts.storage import Storage
from ghostos.container import Provider, Container, ABSTRACT
from ghostos.core.ghosts import Workspace


class StorageConfigs(Configs):
    """
    基于 storage 实现的 configs.
    """

    def __init__(self, storage: Storage, conf_dir: str):
        self._storage = storage.sub_storage(conf_dir)

    def get(self, conf_type: Type[C], file_name: Optional[str] = None) -> C:
        path = conf_type.conf_path()
        content = self._storage.get(file_name)
        return conf_type.load(content)


class ConfigsByStorageProvider(Provider[Configs]):

    def __init__(self, conf_dir: str):
        self._conf_dir = conf_dir

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Configs]:
        return Configs

    def factory(self, con: Container) -> Optional[Configs]:
        storage = con.force_fetch(Storage)
        return StorageConfigs(storage, self._conf_dir)


class WorkspaceConfigsProvider(Provider[Configs]):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[ABSTRACT]:
        return Configs

    def factory(self, con: Container) -> Optional[ABSTRACT]:
        workspace = con.force_fetch(Workspace)
        return StorageConfigs(workspace.configs(), "")
