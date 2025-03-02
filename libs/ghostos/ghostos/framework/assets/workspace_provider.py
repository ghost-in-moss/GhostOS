from typing import Optional, Type
from abc import ABC, abstractmethod

from ghostos.contracts.assets import (
    StorageFileAssets, FileAssets,
)
from ghostos.contracts.workspace import Workspace
from ghostos_container import Container, Provider, INSTANCE


class WorkspaceFileAssetsProvider(Provider, ABC):
    """
    workspace based image asset provider.
    """

    def __init__(self, dirname: str):
        self._dirname = dirname

    def singleton(self) -> bool:
        return True

    @abstractmethod
    def contract(self) -> Type[FileAssets]:
        pass

    def factory(self, con: Container) -> Optional[INSTANCE]:
        ws = con.force_fetch(Workspace)
        storage = ws.runtime().sub_storage(self._dirname)
        return StorageFileAssets(storage)
