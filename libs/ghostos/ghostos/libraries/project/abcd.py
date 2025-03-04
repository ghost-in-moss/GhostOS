from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
from typing_extensions import Self
import pathlib


class Directory(ABC):
    """
    this is a useful tool to manage a directory or a project in agentic way.
    the principles of files management are:
    1. You can manage the files and sub dirs in this directory, but not parent directories.
    2. Markdown as knowledge: the Markdown files in the directory are the knowledge for you.
    3. Directory library can not add/remove/move files or directory itself. Other library may do.

    this library will get more features in future versions.
    """

    path: pathlib.Path
    """the pathlib.Path object of the directory"""

    ignores: List[str]
    """the patterns to ignore file or directory. combined with `.gitignore`"""

    watching: List[str]
    """watching filenames (relative to this directory), the content of the file will display in the context."""

    @abstractmethod
    def lists(
            self, *,
            prefix: str = "",
            recursion: int = 0,
            files: bool = True,
            dirs: bool = True,
    ) -> str:
        """
        list sub filenames and directories as string.
        :param prefix: the relative path that start the listing.
        :param recursion: the recursion depth, 0 means no recursion. < 0 means endless recursion.
        :param dirs: True => list dirs
        :param files: True => list files
        :return: formated string of directory
        """
        pass

    @abstractmethod
    def subdir(self, path: str) -> Self:
        """
        get subdirectory instance by path relative to this directory.
        :param path: the relative path which must be a directory.
        :return: Directory instance.
        """
        pass

    @abstractmethod
    def describe(self, path: str, desc: str) -> None:
        """
        describe a sub file or directory. then you can see the description in the context.
        :param path: relative to this directory.
        :param desc: description.
        """
        pass

    @abstractmethod
    def file(self, filename: str) -> FileEditor:
        """
        get file editor.

        """
        pass


class FileEditor(ABC):
    """
    edit a file.
    """

    path: pathlib.Path
    """the file path object"""

    editable: bool
    """if the file is editable"""

    @abstractmethod
    def read(self, with_line_num: bool = True) -> str:
        """
        read a readable (text mainly) file content.
        if the file is image or audio, send a message of it.
        :param with_line_num: if True, display line number (like 1|... ) at the beginning of each line.
        :return: the content of the file.
        """
        pass

    @abstractmethod
    def write(self, content: str, desc: str = "") -> None:
        """
        write content to the editable file.
        :param content: the content of the file.
        :param desc: description for this file.
        """
        pass

    @abstractmethod
    def insert(self, start: int, end: int, content: str) -> None:
        """
        write content into the editable file, replace the origin block from start line to end line.
        if start line equals end line, insert content at the start line.
        :param start: the start line of content.
        :param end: the end line of content. if negative, count from the end of the file.
        :param content: the content of the file.
        """
        pass

    @abstractmethod
    def ask(self, question: str) -> str:
        """
        ask question about the file, some llm will answer the question.
        :param question: your question about the file
        :return: answer
        """
        pass
