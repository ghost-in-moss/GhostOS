from .workspace_provider import WorkspaceFileAssetsProvider
from typing import Type

from ghostos.contracts.assets import (
    AudioAssets,
)


class WorkspaceAudioAssetsProvider(WorkspaceFileAssetsProvider):

    def __init__(self, dirname: str = "audios"):
        super().__init__(dirname)

    def contract(self) -> Type[AudioAssets]:
        return AudioAssets
