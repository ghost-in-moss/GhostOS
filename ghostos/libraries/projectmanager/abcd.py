from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from typing_extensions import Self
from ghostos.prompter import POM
from ghostos.libraries.terminal import Terminal
from pydantic import BaseModel, Field
from pathlib import Path


class ProjectManager(POM, ABC):
    """
    the manager useful for managing a filesystem based project.
    """

    class ProjectConfig(BaseModel):
        name: str = Field(
            default="",
            description="The name of the project",
        )
        ignores: List[str] = Field(
            default_factory=lambda: [
                '__pycache__', '*.pyc', '*.pyo', 'venv', '.idea', r'^\.', '*.log', '.git',
                'dist',
            ],
            description="List of regex patterns of ignored file or directory. combined with `.gitignore`",
        )
        memo: Dict[str, str] = Field(
            default_factory=dict,
            description="the global memos of how to understand this project. "
        )
        instructions: Dict[str, str] = Field(
            default_factory=dict,
            description="the global instructions of how to maintain this project. "
        )
        watching: List[str] = Field(
            default_factory=list,
            description="the watching path notes of the project",
        )

    config: ProjectConfig
    """the config of the project manager. modify the values can change default behaviors. """

    terminal: Terminal
    """terminal that you can use to interact with the operating system."""

    @abstractmethod
    def save_note(self, relative_path: str, *, desc: str = None, notes: Dict[str, str] = None) -> bool:
        """
        save note to a path that you can read later as long-term memory.
        :param relative_path: relative path to the project root.
        :param desc: description of the path (is directory or file? type? usage? cares? in 200 words)
        :param notes: notes of the path in dictionary, key is note topic, value is note content
        :return: False if the file or directory does not exist.
        """
        pass

    @abstractmethod
    def get_note(self, relative_path: str) -> Tuple[str, Dict[str, str]]:
        """
        get the note of a path
        :param relative_path: relative path to the project root.
        :return: (description, notes_dictionary)
        """
        pass

    @abstractmethod
    def list_paths(self, prefix: str = '', depth: int = 0, limit: int = 30) -> str:
        """
        list the paths under the given prefix, and show description of the path within.

        :param prefix: directory path relative to the project root.
        :param depth: the list depth
        :param limit: the limit of listed files.
        :return: directory and files in the Markdown list pattern, which means:
            * `+` means is a directory
            * `-` means is a file
            * `:` means path note description follows.
            * indent tells the depth of the path.
        """
        pass

    @abstractmethod
    def read_file(self, filename: str) -> str:
        """
        quick method to get content of a file.
        :param filename: relative to the project root
        :return: content str
        """
        pass

    @abstractmethod
    def save_file(self, filename: str, content: str) -> None:
        """
        quick method to update a file.
        :param filename: the relative path to the project root.
        :param content: the content of the file.
        """
        pass


class Directory(ABC):
    """
    this is a useful tool to manage a directory or a project in agentic way.
    the principles of files management are:
    1. You can manage the files and sub dirs in this directory, but not parent directories.
    2. Markdown as knowledge: the Markdown files in the directory are the knowledge for you.
    3. Directory library can not add/remove/move files or directory itself. Other library may do.

    this library will get more features in future versions.
    """

    path: Path
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
    def lists(
            self, *,
            prefix: str = "",
            depth: int = 0,
            files: bool = True,
            dirs: bool = True,
    ) -> str:
        """
        list sub filenames and directories as string.
        :param prefix: the relative path that start the listing.
        :param depth: the recursion depth, 0 means no recursion.
        :param dirs: True => list dirs
        :param files: True => list files
        """
        pass

    @abstractmethod
    def sub(self, path: str) -> Self:
        """
        get subdirectory instance by path relative to this directory.
        :param path: the relative path which must be a directory.
        :return: Directory instance.
        """
        pass

    @abstractmethod
    def abspath(self, path: str = "") -> Path:
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

    @abstractmethod
    def read(self, path: str) -> str:
        """
        read a readable (text mainly) file content.
        you can also get the file object by other library.
        :param path: the filename relative to this directory.
        :return: the content of the file.
        """
        pass

    @abstractmethod
    def write(self, path: str, content: str, desc: str = "") -> None:
        """
        write content to a file.
        :param path: filename relative to this directory, must exist.
        :param content: the content of the file.
        :param desc: description for this file.
        """
        pass
