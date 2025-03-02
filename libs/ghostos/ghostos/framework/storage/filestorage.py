import os
import re
from typing import Optional, Iterable
from ghostos_container import Provider, Container, ABSTRACT
from ghostos.contracts.storage import Storage, FileStorage

__all__ = ["FileStorageProvider", "FileStorageImpl"]


class FileStorageImpl(FileStorage):
    """
    FileStorage implementation based on python filesystem.
    Simplest implementation.
    """

    def __init__(self, dir_: str):
        self._dir: str = os.path.abspath(dir_)

    def abspath(self) -> str:
        return self._dir

    def get(self, file_path: str) -> bytes:
        file_path = self._join_file_path(file_path)
        with open(file_path, 'rb') as f:
            return f.read()

    def remove(self, file_path: str) -> None:
        file_path = self._join_file_path(file_path)
        os.remove(file_path)

    def exists(self, file_path: str) -> bool:
        file_path = self._join_file_path(file_path)
        return os.path.exists(file_path)

    def _join_file_path(self, path: str) -> str:
        file_path = os.path.join(self._dir, path)
        file_path = os.path.abspath(file_path)
        if not file_path.startswith(self._dir):
            raise FileNotFoundError(f"file path {path} is not allowed")
        return file_path

    def put(self, file_path: str, content: bytes) -> None:
        file_path = self._join_file_path(file_path)
        if not file_path.startswith(self._dir):
            raise FileNotFoundError(f"file path {file_path} is not allowed")
        file_dir = os.path.dirname(file_path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        with open(file_path, 'wb') as f:
            f.write(content)

    def sub_storage(self, relative_path: str) -> "FileStorage":
        if not relative_path:
            return self
        dir_path = self._join_file_path(relative_path)
        return FileStorageImpl(dir_path)

    def dir(self, prefix_dir: str, recursive: bool, patten: Optional[str] = None) -> Iterable[str]:
        dir_path = self._join_file_path(prefix_dir)
        for root, ds, fs in os.walk(dir_path):
            # 遍历单层的文件名.
            for file_name in fs:
                if self._match_file_pattern(file_name, patten):
                    relative_path = file_name.lstrip(dir_path)
                    yield relative_path.lstrip('/')

            # 深入遍历目录.
            if recursive and ds:
                for _dir in ds:
                    sub_dir_iterator = self.dir(_dir, recursive, patten)
                    for file_name in sub_dir_iterator:
                        yield file_name

    @staticmethod
    def _match_file_pattern(filename: str, pattern: Optional[str]) -> bool:
        if pattern is None:
            return True
        r = re.search(pattern, filename)
        return r is not None


class FileStorageProvider(Provider[FileStorage]):

    def __init__(self, dir_: str):
        self._dir: str = dir_

    def singleton(self) -> bool:
        return True

    def aliases(self) -> Iterable[ABSTRACT]:
        yield Storage

    def factory(self, con: Container) -> Optional[Storage]:
        return FileStorageImpl(self._dir)
