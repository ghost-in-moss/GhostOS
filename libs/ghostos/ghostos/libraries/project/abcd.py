from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Union
from types import FunctionType, ModuleType
from typing_extensions import Self
from pydantic import BaseModel, Field
from ghostos.abcd import Operator
from ghostos.libraries.pyeditor import PyModuleEditor
from ghostos_moss import Exporter
import pathlib

_IMPORT_PATH = str
"""the python import path in pattern [modulename:attr_name], e.g. 'foo', 'foo.bar', 'foo.bar:baz' """


class PyDevCtx(BaseModel, ABC):
    """
    python context for a certain kind of develop jobs.
    you can use it to remember important python context and never forget them in long-term.
    """

    title: str = Field(description="title for this context")

    desc: str = Field(default="", description="description for this context")

    instructions: Dict[str, str] = Field(
        default_factory=dict,
        description="write instructions by yourself to follow"
    )

    notes: Dict[str, str] = Field(
        default_factory=dict,
        description="record something in case of forgetting"
    )

    examples: List[str] = Field(
        default_factory=list,
        description="use python module as examples for developing.",
    )

    interfaces: List[_IMPORT_PATH] = Field(
        default_factory=list,
        description=(
            "watching a bunch of python module/class/func interfaces."
            "dev context will provide the interface of them for you"
        )
    )

    sources: List[_IMPORT_PATH] = Field(
        default_factory=list,
        description="watching a bunch of python module/class/func sources."
    )

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
        """
        pass

    @abstractmethod
    def full_context(self) -> str:
        """
        dump the context into nature language string.
        """
        pass


class Directory(ABC):
    """
    this is a useful tool to manage a directory or a project in agentic way.
    the principles of files management are:
    1. You can manage the files and sub dirs in this directory, but not parent directories.
    2. Markdown as knowledge: the Markdown files in the directory are the knowledge for you.
    this library will get more features in future versions.
    """

    path: pathlib.Path
    """the pathlib.Path object of the directory"""

    ctx: PyDevCtx
    """the dev context of this directory"""

    @abstractmethod
    def full_context(self) -> str:
        """
        :return: the context of the directory
        """
        pass

    @abstractmethod
    def dev_contexts(self) -> Dict[str, PyDevCtx]:
        """
        :return: all the dev contexts in this directory.
        """
        pass

    @abstractmethod
    def new_dev_context(self, title: str, desc: str) -> PyDevCtx:
        """
        create a new dev context for some jobs.
        the context will save to the directory
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
        :param path: the relative path which must be a directory. must exist or raise ValueError.
        :return: Directory instance.

        if you want to create directory, use terminal if you got one.
        """
        pass

    @abstractmethod
    def describe(self, path: str, desc: str) -> None:
        """
        describe a sub file or directory. then you can see the description in the context.
        :param path: relative to this directory. if `.`, means describe the directory itself
        :param desc: description.
        """
        pass

    @abstractmethod
    def mkdir(self, subdir: str, desc: str, dev_ctx: Union[PyDevCtx, None] = None) -> bool:
        """
        make a subdirectory with description and dev_ctx
        :param subdir: directory path relative to this directory.
        :param desc: description of the directory.
        :param dev_ctx: pass the dev_ctx to this directory. not neccessary, do it only if you know what you're doing.
        :return: if False, directory already exists.
        """
        pass

    @abstractmethod
    def touch(self, sub_file: str, desc: str, dev_ctx: Union[PyDevCtx, None] = None) -> bool:
        """
        touch a file with description and Optional[dev_ctx]
        """
        pass

    @abstractmethod
    def edit(self, file_path: str) -> File:
        """
        focus to edit the file in the directory
        the file must exist or raise FileNotFoundError.

        :param file_path: relative to the working directory. if None, don't focus on any file.
        """
        pass

    @abstractmethod
    def focus(self, file_path: Union[str, None]) -> Union[File, None]:
        """
        focus on a file and create editing file object.
        :param file_path: if None, focus on nothing, spare tokens.
        :return: if file_path is None, return None
        """
        pass

    @abstractmethod
    def save_data(self) -> None:
        """
        save the changes from dev context changes/describe/focus
        better way to call save_data by use `with statement`
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        if exit the directory context without errors, the dev data of this directory will be saved.
        """
        if not exc_val:
            self.save_data()


class File(ABC):
    path: pathlib.Path
    """the pathlib.Path object of the directory"""

    ctx: PyDevCtx
    """the dev context of this file"""

    @abstractmethod
    def read(self, line_number: bool = True, detail: bool = True) -> str:
        """
        read content from the file.
        :param line_number: if True, add line number at the beginning of each line like `1|...`
        :param detail: if True, add more information about the file, the real content of the file will be embraced with <content>...</content> mark
        """
        pass

    @abstractmethod
    def write(self, content: str, append: bool = False) -> None:
        """
        write content to the file.
        """
        pass

    @abstractmethod
    def insert(self, content: str, start: int = -1, end: int = -1) -> None:
        """
        use content to relace the origin content lines > start line and <= end line.
        """
        pass

    @abstractmethod
    def continuous_write(self, instruction: str, start: int = -1, end: int = -1, max_round: int = 10) -> Operator:
        """
        considering your output is limited, you can use this method to start a continuous writing in multi-turns.
        only use it when you are planning to write something beyond your max-tokens limit.
        :param instruction: about what you are doing, will remind it to you at each turn
        :param start: start index: the writing start at line
        :param end: end index: the writing end before (eqt) line
        :param max_round: maximum round for this writing.
        :return: remember to return the mind operator, which will operate the multi-turns writing.
        """
        pass


class ProjectManager(ABC):
    """
    project manager
    you are provided with Directory, and DevContext that helping you to watch useful tools.
    """

    root: Directory
    """the root directory of the project."""

    working: Directory
    """the current directory of the project."""

    @abstractmethod
    def work_on(self, dir_path: str) -> Operator:
        """
        change the working directory to dir_path, always relative to the root directory.
        :param dir_path: if empty or `~`, will check out to the root.
        """
        pass

    @abstractmethod
    def edit_pymodule(self, modulename: str) -> PyModuleEditor:
        """
        edit a python module, if editable.
        :param modulename: the full import name of the module
        """
        pass


class ProjectExports(Exporter):
    """
    the exports for projects.
    """

    ProjectManager = ProjectManager
    PyDevCtx = PyDevCtx
    File = File
    Directory = Directory
    PyModuleEditor = PyModuleEditor
