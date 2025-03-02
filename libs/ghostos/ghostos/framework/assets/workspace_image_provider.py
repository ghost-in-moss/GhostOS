from .workspace_provider import WorkspaceFileAssetsProvider
from typing import Type

from ghostos.contracts.assets import (
    ImageAssets,
)


class WorkspaceImageAssetsProvider(WorkspaceFileAssetsProvider):

    def __init__(self, dirname: str = "images"):
        super().__init__(dirname)

    def contract(self) -> Type[ImageAssets]:
        return ImageAssets
