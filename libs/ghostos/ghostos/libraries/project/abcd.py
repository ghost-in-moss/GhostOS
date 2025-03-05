from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Union
from types import FunctionType, ModuleType
from typing_extensions import Self
import pathlib


class DevDesk(ABC):
    """
    the dev contxt for a certain developing task.
    You can change the attributes to
    """

    title: str
    """title of this dev desk"""

    directory: str
    """the directory of this dev desk located. """

    description: str
    """describe what-for of this dev desk"""

    _IMPORT_PATH = str
    """the python import path in pattern [modulename:attr_name], e.g. 'foo', 'foo.bar', 'foo.bar:baz' """

    watching_interfaces: List[_IMPORT_PATH]
    """
    watching a bunch of python module/class/func interfaces. 
    dev context will provide the interface of them for you
    """

    watching_source: List[_IMPORT_PATH]
    """
    watching a bunch of python module/class/func sources.
    """

    knowledge: List[str]
    """
    filenames of markdown files that providing knowledge in the context. 
    a markdown file is a piece of knowledge. 
    """

    reading_files: List[str]
    """
    the filenames (relative to the directory) that you are reading.
    the content of the files will display in context, with line number before each line.
    """

    notes: Dict[str, str]
    """
    write notes that you should not forget. 
    """

    @abstractmethod
    def dump_context(self) -> str:
        """
        :return: the context of this DevContext as a string
        """
        pass

    @abstractmethod
    def read_interface(
            self,
            target: Union[str, FunctionType, ModuleType, type],
            *,
            watching: bool = False,
    ) -> str:
        """
        read code interface from a target.
        :param target:  import path or objects that can be called by inspect.getsource
        :param watching: if watching, will always watch it.
        :return:
        """
        pass

    @abstractmethod
    def read_source(
            self,
            target: Union[str, FunctionType, ModuleType, type],
            *,
            watching: bool = False,
    ) -> str:
        """
        read source code from a target.
        :param target:  import path or objects that can be called by inspect.getsource
        :param watching: if watching, will always watch it.
        :return:
        """
        pass

    @abstractmethod
    def get_context(self, title: str) -> Self:
        """
        get an existing dev context by title, or create one.
        :param title: the title of the dev context
        """
        pass

    @abstractmethod
    def switch(self, dev_context: Self):
        """
        switch self to another dev context.
        """
        pass

    @abstractmethod
    def save(self) -> None:
        """
        save the current dev context.
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

    path: pathlib.Path
    """the pathlib.Path object of the directory"""

    default_list_depth: int
    """the list depth for the directory context"""

    ignores: List[str]
    """the patterns to ignore file or directory. combined with `.gitignore`"""

    @abstractmethod
    def dump_context(self) -> str:
        """
        :return: the context of the directory
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
    def describe(self, path: str, desc: str) -> None:
        """
        describe a sub file or directory. then you can see the description in the context.
        :param path: relative to this directory.
        :param desc: description.
        """
        pass
