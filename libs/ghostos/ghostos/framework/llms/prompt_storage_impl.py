from typing import Optional

from ghostos.contracts.storage import Storage
from ghostos.core.llms import Prompt
from ghostos.core.llms.prompt import PromptStorage
from ghostos_common.helpers import yaml_pretty_dump
import yaml


class PromptStorageImpl(PromptStorage):

    def __init__(self, storage: Storage):
        self._storage = storage

    @staticmethod
    def _get_filename(prompt_id: str) -> str:
        filename = f"{prompt_id}.prompt.yml"
        return filename

    def save(self, prompt: Prompt) -> None:
        data = prompt.model_dump(exclude_defaults=True)
        filename = self._get_filename(prompt.id)
        content = yaml_pretty_dump(data)
        self._storage.put(filename, content.encode())

    def get(self, prompt_id: str) -> Optional[Prompt]:
        filename = self._get_filename(prompt_id)
        if self._storage.exists(filename):
            content = self._storage.get(filename)
            data = yaml.safe_load(content)
            return Prompt(**data)
        return None
