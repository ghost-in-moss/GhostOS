import os
from typing import Optional, AnyStr, Dict, Type, Union
from abc import ABC, abstractmethod
from ghostiss.container import Provider, Container, Contract

__all__ = ['Storage', 'FileStorage', 'FileStorageProvider']


class Storage(ABC):

    @abstractmethod
    def get(self, file_name: str) -> AnyStr:
        pass

    @abstractmethod
    def put(self, file_name: str, content: bytes) -> None:
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


class FileStorageProvider(Provider):

    def __init__(self, dir_: str):
        self._dir: str = dir_

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Storage

    def factory(self, con: Container, params: Optional[Dict] = None) -> Optional[Contract]:
        return FileStorage(self._dir)
