from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path


class Directory(ABC):
    abspath: str

    @abstractmethod
    def pathlib(self) -> Path:
        """
        :return: pathlib.Path object of the directory
        """
        pass


class File(ABC):
    abspath: str

    @abstractmethod
    def pathlib(self) -> Path:
        pass


class DirectoryEditor(ABC):
    """
    understand directories and edit them
    """

    @abstractmethod
    def abspath(self) -> str:
        """
        :return: the absolute path of the current directory
        """
        pass

    @abstractmethod
    def summarize(self, summary: str) -> None:
        """
        summarize the current directory
        :param summary: less than 200 characters in a single line
        """
        pass

    @abstractmethod
    def edit_file(self, relative_path: str, create_nx: bool = False) -> "FileEditor":
        """
        create FileEditor to edit file, or just read about it
        :param relative_path: relative path from the current directory
        :param create_nx: create a new file if file not exists
        :return: FileEditor
        :exception: FileNotFoundError
        """
        pass

    @abstractmethod
    def edit_dir(self, relative_dir: str, create_nx: bool = True) -> "DirectoryEditor":
        """
        create DirectoryEditor
        :param relative_dir: relative path from the current directory
        :param create_nx: create a new directory if directory not exists
        :return: editor of the target directory
        :exception: FileNotFoundError
        """
        pass

    @abstractmethod
    def list(
            self, *,
            depth: int = 0,
            list_dir: bool = True,
            list_file: bool = True,
            pattern: str = "*",
            absolute: bool = False,
            ignores: Optional[str] = None,
            formated: bool = True,
            summary: bool = True,
    ) -> List[str]:
        """
        list the directories and files in the current directory

        :param depth: the recursive directory depth. 0 means current directory only
        :param list_dir: if True, list the directories. if False, will not list recursively
        :param list_file: if True, list the files.
        :param pattern: regex pattern to filter files, not directories.
        :param absolute: if True, list the files in absolute path, otherwise relative path.
        :param ignores: regex pattern to ignore files. None means default ignore rules.
        :param formated: if True, list result will be formatted as a  list tree in markdown,
               '+' means directory, '-' means file.
               if false, result will be list of string.

        :param summary: if True, each file will be followed with its summary.
        :return: list of the files and directories. you can use "\n".join(listed) to display them.

        if you want raw absolute filenames, you shall set formated and summary False, and absolute True
        """
        pass


class FileEditor(ABC):
    """
    useful to edit a certain file.
    """

    filename: str

    @abstractmethod
    def summarize(self, summary: str) -> None:
        """
        summarize the current editing file
        :param summary: less than 200 characters in a single line
        :return:
        """
        pass

    @abstractmethod
    def read(self, show_line_num: bool = False, start_line: int = 0, end_line: int = -1) -> str:
        """
        read the content of the file
        :param show_line_num: if True, each line will start with line number and `|`.
               With show_line_num True is easy to see line number, but not the origin content. don't mixed up.
        :param start_line: start line
        :param end_line: end line number. if negative, means length + end_line
        :return: content of the file

        If you want origin content of the file, remember show_line_num shall be False,
        otherwise you get line numbers before each line.
        """
        pass

    @abstractmethod
    def replace_block(self, replacement: str, start_line: int = 0, end_line: int = -1) -> str:
        """
        replace the block content of the file
        :param replacement: new content of the block replacement
        :param start_line: block start line
        :param end_line: block end line
        :return: the replaced origin block content
        """
        pass

    @abstractmethod
    def replace(self, origin: str, replace: str, count: int = -1) -> None:
        """
        replace a curtain content of the file
        :param origin: old content
        :param replace: new content
        :param count: times that shall be replaced. if negative, replace all times
        """
        pass

    @abstractmethod
    def append(self, content: str) -> None:
        """
        append content to the tail of the file
        """
        pass

    @abstractmethod
    def insert(self, content: str, start_line: int) -> None:
        """
        insert content starting at position line into the file
        """
        pass
