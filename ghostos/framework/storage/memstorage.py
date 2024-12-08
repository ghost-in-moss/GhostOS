from typing import Optional, Iterable, Dict

from ghostos.contracts.storage import FileStorage
from os.path import join

__all__ = ["MemStorage"]


class MemStorage(FileStorage):

    def __init__(self, saved: Dict[str, bytes] = None, namespace: str = ""):
        self._namespace = namespace
        self._saved: Dict[str, bytes] = saved if saved else {}

    def abspath(self) -> str:
        return "/test/mem/"

    def sub_storage(self, relative_path: str) -> "Storage":
        namespace = self._namespace
        if relative_path:
            namespace = namespace + "/" + relative_path
        return MemStorage(self._saved, namespace)

    def get(self, file_path: str) -> bytes:
        key = join(self._namespace, file_path)
        key = key.lstrip('/')
        if key not in self._saved:
            raise KeyError(key)
        return self._saved.get(key)

    def exists(self, file_path: str) -> bool:
        key = join(self._namespace, file_path)
        key = key.lstrip('/')
        return key in self._saved

    def remove(self, file_path: str) -> None:
        key = join(self._namespace, file_path)
        key = key.lstrip('/')
        del self._saved[key]

    def put(self, file_path: str, content: bytes) -> None:
        key = join(self._namespace, file_path)
        key = key.lstrip('/')
        self._saved[key] = content

    def dir(self, prefix_dir: str, recursive: bool, patten: Optional[str] = None) -> Iterable[str]:
        for key in self._saved.keys():
            yield key
