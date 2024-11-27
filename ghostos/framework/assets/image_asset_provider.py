from typing import Optional

from ghostos.contracts.assets import ImagesAsset, StorageImagesAsset
from ghostos.contracts.workspace import Workspace
from ghostos.container import Container, Provider, INSTANCE


class WorkspaceImagesAssetProvider(Provider[ImagesAsset]):
    """
    workspace based image asset provider.
    """

    def __init__(self, dirname: str = "images"):
        self._dirname = dirname

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[INSTANCE]:
        ws = con.force_fetch(Workspace)
        storage = ws.assets().sub_storage(self._dirname)
        return StorageImagesAsset(storage)
