import os
import re
from typing import Optional, AnyStr, Dict, Type, Iterable
from abc import ABC, abstractmethod
from ghostiss.container import Provider, Container, ABSTRACT

__all__ = ['Storage', 'FileStorage', 'FileStorageProvider']


class Storage(ABC):

    @abstractmethod
    def sub_storage(self, relative_path: str) -> "Storage":
        """
        生成一个次级目录下的 storage.
        :param relative_path:
        :return:
        """
        pass

    @abstractmethod
    def get(self, file_path: str) -> AnyStr:
        """
        获取一个 Storage 路径下一个文件的内容.
        :param file_path: storage 下的一个相对路径.
        """
        pass

    @abstractmethod
    def put(self, file_path: str, content: bytes) -> None:
        """
        保存一个文件的内容到 file_path .
        :param file_path: storage 下的一个相对路径.
        :param content: 文件的内容.
        """
        pass

    @abstractmethod
    def dir(self, prefix_dir: str, recursive: bool, patten: Optional[str] = None) -> Iterable[str]:
        """
        遍历一个路径下的文件, 返回相对的文件名.
        :param prefix_dir: 目录的相对路径位置.
        :param recursive: 是否递归查找.
        :param patten: 文件的正则规范.
        :return: 多个文件路径名.
        """
        pass


class FileStorage(Storage):

    def __init__(self, dir_: str):
        self._dir: str = dir_

    def get(self, file_path: str) -> AnyStr:
        file_path = self._join_file_path(file_path)
        with open(file_path, 'rb') as f:
            return f.read()

    def _join_file_path(self, path: str) -> str:
        file_path = os.path.join(self._dir, path)
        file_path = os.path.abspath(file_path)
        if not file_path.startswith(self._dir):
            raise FileNotFoundError(f"file path {path} is not allowed")
        return file_path

    def put(self, file_path: str, content: bytes) -> None:
        file_path = self._join_file_path(file_path)
        file_dir = os.path.dirname(file_path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        with open(file_path, 'wb') as f:
            f.write(content)

    def sub_storage(self, relative_path: str) -> "Storage":
        dir_path = self._join_file_path(relative_path)
        return FileStorage(dir_path)

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


class FileStorageProvider(Provider[Storage]):

    def __init__(self, dir_: str):
        self._dir: str = dir_

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Storage]:
        return Storage

    def factory(self, con: Container) -> Optional[Storage]:
        return FileStorage(self._dir)
