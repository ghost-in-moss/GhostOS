from typing import Optional

from ghostos.contracts.storage import Storage
from ghostos.contracts.workspace import Workspace
from ghostos.core.llms import Prompt
from ghostos.core.llms.prompt import PromptStorage
from ghostos.container import Provider, Container, INSTANCE
import json


class PromptStorageImpl(PromptStorage):

    def __init__(self, storage: Storage):
        self._storage = storage

    @staticmethod
    def _get_filename(prompt_id: str) -> str:
        filename = f"{prompt_id}.prompt.json"
        return filename

    def save(self, prompt: Prompt) -> None:
        data = prompt.model_dump_json(indent=2)
        filename = self._get_filename(prompt.id)
        self._storage.put(filename, data.encode())

    def get(self, prompt_id: str) -> Optional[Prompt]:
        filename = self._get_filename(prompt_id)
        if self._storage.exists(filename):
            content = self._storage.get(filename)
            data = json.loads(content)
            return Prompt(**data)
        return None


class PromptStorageProvider(Provider[PromptStorage]):
    def __init__(self, relative_path: str = "prompts"):
        self._relative_path = relative_path

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[INSTANCE]:
        ws = con.force_fetch(Workspace)
        storage = ws.runtime().sub_storage(self._relative_path)
        return PromptStorageImpl(storage)
