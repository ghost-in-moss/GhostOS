from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from typing_extensions import Self
from ghostos.prompter import POM
from ghostos.libraries.terminal import Terminal
from pydantic import BaseModel, Field
import pathlib


class Project(POM, ABC):
    """
    the manager useful for managing a filesystem based project.
    """

    root: Directory
    """root path of the project"""


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
    def dump_context(self) -> str:
        """
        get the context of this directory. `context` means:

        * `instruction.md` instructions of how to maintain this directory.
        * list of sub filenames and directories (in Markdown list pattern), filtered by ignores.
        * the watching files contents in this directory.
        * the specialist agents for the maintainer of this directory.
        :return:
        """
        pass

    @abstractmethod
    def instruction(self) -> str:
        """
        :return: the content of the instruction.md
        """
        pass

    @abstractmethod
    def ignored(self) -> List[str]:
        """
        :return: the ignore patterns combine self.ignores with `.gitignore`
        """
        pass

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
    def abspath(self, path: str = "") -> pathlib.Path:
        """
        get the absolute path object from a relative one
        :param path: path relative to this directory.
        :return: pathlib.Path object
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


class File(ABC):
    path: pathlib.Path

    editable: bool
    """if the file is editable"""

    @abstractmethod
    def read(self) -> str:
        """
        read a readable (text mainly) file content.
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
    def ask(self, question: str) -> str:
        """
        ask question about the file, some llm will answer the question.
        :param question: your question about the file
        :return: answer
        """
        pass
