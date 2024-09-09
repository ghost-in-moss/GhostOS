from typing import Optional, Iterable, AnyStr, Dict

from ghostos.contracts.storage import Storage
from os.path import join

__all__ = ["MemStorage"]


class MemStorage(Storage):

    def __init__(self, saved: Dict[str, bytes] = None, namespace: str = ""):
        self._namespace = namespace
        self._saved: Dict[str, bytes] = saved if saved else {}

    def sub_storage(self, relative_path: str) -> "Storage":
        namespace = self._namespace
        if relative_path:
            namespace = namespace + "/" + relative_path
        return MemStorage(self._saved, namespace)

    def get(self, file_path: str) -> bytes:
        key = join(self._namespace, file_path)
        if key not in self._saved:
            raise KeyError(key)
        return self._saved.get(key)

    def exists(self, file_path: str) -> bool:
        key = join(self._namespace, file_path)
        return key in self._saved

    def put(self, file_path: str, content: bytes) -> None:
        key = join(self._namespace, file_path)
        self._saved[key] = content

    def dir(self, prefix_dir: str, recursive: bool, patten: Optional[str] = None) -> Iterable[str]:
        for key in self._saved.keys():
            yield key
