from typing import Optional, Type

from ghostos.contracts.workspace import Workspace
from ghostos.framework.storage import FileStorage, FileStorageImpl
from ghostos_container import Provider, Container, INSTANCE


class BasicWorkspace(Workspace):

    def __init__(
            self,
            workspace_storage: FileStorage,
            runtime_path: str = "runtime",
            configs_path: str = "configs",
            assets_path: str = "assets",
    ):
        self._storage: FileStorage = workspace_storage
        self._runtime_storage = workspace_storage.sub_storage(runtime_path)
        self._configs_storage = workspace_storage.sub_storage(configs_path)
        self._assets_storage = workspace_storage.sub_storage(assets_path)

    def root(self) -> FileStorage:
        return self._storage

    def runtime(self) -> FileStorage:
        return self._runtime_storage

    def runtime_cache(self) -> FileStorage:
        return self._runtime_storage.sub_storage("cache")

    def assets(self) -> FileStorage:
        return self._assets_storage

    def configs(self) -> FileStorage:
        return self._configs_storage


class BasicWorkspaceProvider(Provider):
    """
    basic workspace provider
    """

    def __init__(
            self,
            workspace_dir: str,
            runtime_path: str = "runtime",
            configs_path="configs",
            assets_path: str = "assets",
    ):
        """
        :param workspace_dir: relative workspace dir to the root path
        :param runtime_path: relative runtime path to the workspace dir
        :param configs_path: relative configs path to the workspace dir
        """
        self._root_path = workspace_dir
        self._runtime_path = runtime_path
        self._configs_path = configs_path
        self._assets_path = assets_path

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[INSTANCE]:
        return Workspace

    def factory(self, con: Container) -> Optional[INSTANCE]:
        root_storage = FileStorageImpl(self._root_path)
        return BasicWorkspace(
            root_storage,
            runtime_path=self._runtime_path,
            configs_path=self._configs_path,
            assets_path=self._assets_path,
        )
