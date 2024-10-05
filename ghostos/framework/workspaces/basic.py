from typing import Optional, Type

from ghostos.core.ghosts.workspace import Workspace
from ghostos.contracts.storage import FileStorage
from ghostos.container import Provider, Container, ABSTRACT


class BasicWorkspace(Workspace):

    def __init__(
            self,
            root_storage: FileStorage,
            runtime_path: str = "runtime",
            configs_path="configs",
            source_path="sources",
    ):
        self._root_storage: FileStorage = root_storage
        self._runtime_storage = root_storage.sub_storage(runtime_path)
        self._configs_storage = root_storage.sub_storage(configs_path)
        self._source_storage = root_storage.sub_storage(source_path)

    def root(self) -> FileStorage:
        return self._root_storage

    def runtime(self) -> FileStorage:
        return self._runtime_storage

    def configs(self) -> FileStorage:
        return self._configs_storage

    def source(self) -> FileStorage:
        return self._source_storage


class BasicWorkspaceProvider(Provider):
    """
    basic workspace provider
    """

    def __init__(
            self,
            root_dir: str = "",
            runtime_path: str = "runtime",
            configs_path="configs",
            source_path="src",
    ):
        self._root_path = root_dir
        self._runtime_path = runtime_path
        self._configs_path = configs_path
        self._source_path = source_path

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[ABSTRACT]:
        return Workspace

    def factory(self, con: Container) -> Optional[ABSTRACT]:
        storage = con.force_fetch(FileStorage)
        root_storage = storage.sub_storage(self._root_path)
        return BasicWorkspace(
            root_storage,
            runtime_path=self._runtime_path,
            configs_path=self._configs_path,
            source_path=self._source_path,
        )
