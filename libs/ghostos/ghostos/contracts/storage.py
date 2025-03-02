from typing import Optional, Iterable
from abc import ABC, abstractmethod

__all__ = ['Storage', 'FileStorage']


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
    def get(self, file_path: str) -> bytes:
        """
        获取一个 Storage 路径下一个文件的内容.
        :param file_path: storage 下的一个相对路径.
        """
        pass

    @abstractmethod
    def remove(self, file_path: str) -> None:
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """
        if the object exists
        :param file_path: file_path or directory path
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


class FileStorage(Storage, ABC):
    """
    Storage Based on FileSystem.
    """

    @abstractmethod
    def abspath(self) -> str:
        """
        storage root directory's absolute path
        """
        pass

    @abstractmethod
    def sub_storage(self, relative_path: str) -> "FileStorage":
        """
        FileStorage's sub storage is still FileStorage
        """
        pass
