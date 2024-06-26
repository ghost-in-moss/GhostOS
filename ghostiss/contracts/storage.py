import os
import re
from typing import Optional, AnyStr, Dict, Type, Iterable
from abc import ABC, abstractmethod
from ghostiss.container import Provider, Container, CONTRACT

__all__ = ['Storage', 'FileStorage', 'FileStorageProvider']


class Storage(ABC):

    @abstractmethod
    def get(self, file_name: str) -> AnyStr:
        pass

    @abstractmethod
    def put(self, file_name: str, content: bytes) -> None:
        pass

    @abstractmethod
    def dir(self, prefix_dir: str, recursive: bool, patten: Optional[str] = None) -> Iterable[str]:
        pass


class FileStorage(Storage):

    def __init__(self, dir_: str):
        self._dir: str = dir_

    def get(self, file_name: str) -> AnyStr:
        file_path = os.path.join(self._dir, file_name)
        with open(file_path, 'rb') as f:
            return f.read()

    def put(self, file_name: str, content: bytes) -> None:
        file_path = os.path.join(self._dir, file_name)
        with open(file_path, 'wb') as f:
            f.write(content)

    def dir(self, prefix_dir: str, recursive: bool, patten: Optional[str] = None) -> Iterable[str]:
        dir_path = os.path.join(self._dir, prefix_dir)
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

    def _match_file_pattern(self, filename: str, pattern: Optional[str]) -> bool:
        if pattern is None:
            return True
        r = re.search(pattern, filename)
        return r is not None


class FileStorageProvider(Provider[Storage]):

    def __init__(self, dir_: str):
        self._dir: str = dir_

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Storage]:
        return Storage

    def factory(self, con: Container) -> Optional[Storage]:
        return FileStorage(self._dir)
