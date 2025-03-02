from typing import Dict, Optional
from .basic import BasicConfigs


class MemoryConfigs(BasicConfigs):

    def __init__(self, defaults: Optional[Dict] = None):
        defaults = defaults or {}
        self._cache: Dict[str, bytes] = defaults

    def _get(self, relative_path: str) -> bytes:
        if relative_path not in self._cache:
            raise FileNotFoundError(f'{relative_path} is not in cache')
        return self._cache.get(relative_path)

    def _put(self, relative_path: str, content: bytes) -> None:
        self._cache[relative_path] = content

    def _exists(self, relative_path: str) -> bool:
        return relative_path in self._cache
