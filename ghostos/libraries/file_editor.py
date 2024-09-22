from typing import Optional, List, Dict, Tuple, ClassVar
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from pathlib import Path
from ghostos.helpers import yaml_pretty_dump
import yaml
import os


class DirectoryEditor(ABC):

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

    @abstractmethod
    def abspath(self) -> str:
        """
        the full path of the current editing file
        """
        pass

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
    def insert(self, content: str, position: int) -> None:
        """
        insert content starting at position line into the the file
        """
        pass


class FileInfo(BaseModel):
    summary: str = Field(default="", description="summary of the file or the directory")
    filename: str = Field(description="the basename of the file")


class DirIndex(BaseModel):
    DIRECTORY_INDEX_FILE: ClassVar[str] = ".dir_index.yml"

    summary: str = Field(default="", description="summary of the directory")
    files: Dict[str, FileInfo] = Field(default_factory=dict, description="the fileinfo from name to file")
    dirs: Dict[str, Dict] = Field(default_factory=dict, description="the sub directories of the dir")

    def add_file(self, file_info: FileInfo, force: bool) -> None:
        if force or file_info.filename not in self.files:
            self.files[file_info.filename] = file_info

    def add_dir(self, dir_name: str, data: Dict) -> None:
        self.dirs[dir_name] = data

    def sub_dirs(self) -> Dict[str, "DirIndex"]:
        result = {}
        for name, info in self.dirs.items():
            result[name] = DirIndex(**info)
        return result

    @classmethod
    def dir_cache_exists(cls, abspath: str) -> bool:
        filepath = os.path.join(abspath, cls.DIRECTORY_INDEX_FILE)
        return os.path.exists(filepath)

    @classmethod
    def is_cache_file(cls, item: str) -> bool:
        return item.endswith(cls.DIRECTORY_INDEX_FILE)

    def get_file_summary(self, filename: str) -> str:
        if filename in self.files:
            return self.files[filename].summary
        return ""

    def set_file_summary(self, filename: str, summary: str) -> None:
        if filename not in self.files:
            self.files[filename] = FileInfo(filename=filename)
        info = self.files[filename]
        info.summary = summary

    @classmethod
    def load_from_dir_cache(cls, abspath: str) -> "DirIndex":
        filepath = os.path.join(abspath, cls.DIRECTORY_INDEX_FILE)
        if not os.path.exists(filepath):
            return cls()
        with open(filepath, "r") as f:
            content = f.read()
            data = yaml.safe_load(content)
            return cls(**data)

    def save_to_dir_cache(self, abspath: str) -> None:
        filepath = os.path.join(abspath, self.DIRECTORY_INDEX_FILE)
        content = yaml_pretty_dump(self.model_dump(exclude_defaults=True, exclude=set("dirs")))
        with open(filepath, "w") as f:
            f.write(content)


class FileEditorImpl(FileEditor):
    def __init__(self, filepath: str, cache: bool = False):
        self._filepath = filepath
        self._cache = cache
        if not os.path.exists(self._filepath):
            raise FileNotFoundError(f'File "{self._filepath}" does not exist')

    def abspath(self) -> str:
        return self._filepath

    def summarize(self, summary: str) -> None:
        if not self._cache:
            return
        _dir = os.path.dirname(self._filepath)
        index = DirIndex.load_from_dir_cache(_dir)
        filename = Path(self._filepath).name
        index.set_file_summary(filename, summary)
        index.save_to_dir_cache(_dir)

    def read(self, show_line_num: bool = False, start_line: int = 0, end_line: int = -1) -> str:
        with open(self._filepath, 'r') as file:
            lines = file.readlines()
        if end_line < 0:
            end_line = len(lines) + end_line
        lines = lines[start_line:end_line + 1]

        if not show_line_num:
            return ''.join(lines)
        new_lines = []
        digit = len(str(len(lines)))
        for i, line in enumerate(lines, start=start_line):
            idx = str(i)
            prefix = ' ' * (digit - len(idx)) + idx + "|"
            new_lines.append(prefix + line)
        return ''.join(new_lines)

    def replace_block(self, replacement: str, start_line: int = 0, end_line: int = -1) -> str:
        with open(self._filepath, 'r') as file:
            lines = file.readlines()
        if end_line < 0:
            end_line = len(lines) + end_line
        original = ''.join(lines[start_line:end_line + 1])
        lines[start_line:end_line + 1] = replacement.splitlines(keepends=True)
        with open(self._filepath, 'w') as file:
            file.writelines(lines)
        return original

    def replace(self, origin: str, replace: str, count: int = -1) -> None:
        with open(self._filepath, 'r') as file:
            content = file.read()
        new_content = content.replace(origin, replace, count)
        with open(self._filepath, 'w') as file:
            file.write(new_content)

    def append(self, content: str) -> None:
        with open(self._filepath, 'a') as file:
            file.write(content)

    def insert(self, content: str, position: int) -> None:
        with open(self._filepath, 'r') as file:
            lines = file.readlines()
        lines.insert(position, content + '\n')
        with open(self._filepath, 'w') as file:
            file.writelines(lines)


DEFAULT_IGNORES = ['__pycache__', '*.pyc', '*.pyo', 'venv', '.idea', r'^\.', '*.log']


class DirectoryEditorImpl(DirectoryEditor):
    def __init__(
            self,
            dir_path: str,
            ignores: Optional[List[str]] = None,
            cache: bool = False,
    ):
        self._ignores = ignores if ignores is not None else DEFAULT_IGNORES
        self._dir_path = Path(dir_path)
        self._cache = cache
        if not self._dir_path.is_dir():
            raise FileNotFoundError(f"Directory {dir_path} does not exist")
        self._dir_index: DirIndex = DirIndex.load_from_dir_cache(dir_path)

    def abspath(self) -> str:
        return str(self._dir_path)

    def summarize(self, summary: str) -> None:
        if not self._cache:
            return
        self._dir_index = DirIndex.load_from_dir_cache(self.abspath())
        self._dir_index.summary = summary
        self._dir_index.save_to_dir_cache(str(self._dir_path))

    def edit_file(self, relative_path: str, create_nx: bool = False) -> FileEditor:
        file_path = self._dir_path / relative_path
        if not file_path.exists():
            if create_nx:
                file_path.touch()
            else:
                raise FileNotFoundError(f"File {relative_path} not found in {self._dir_path}")
        return FileEditorImpl(str(file_path), cache=self._cache)

    def edit_dir(self, relative_dir: str, create_nx: bool = True) -> DirectoryEditor:
        dir_path = self._dir_path / relative_dir
        if not dir_path.exists():
            if create_nx:
                dir_path.mkdir(parents=True)
            else:
                raise FileNotFoundError(f"Directory {relative_dir} not found in {self._dir_path}")
        return DirectoryEditorImpl(str(dir_path), self._ignores)

    def list(
            self, *,
            depth: int = 0,
            list_dir: bool = True,
            list_file: bool = True,
            pattern: str = "*",
            absolute: bool = False,
            ignores: Optional[List[str]] = None,
            formated: bool = True,
            summary: bool = True,
    ) -> List[str]:
        ignores = ignores or self._ignores

        def _list_dir(path: Path, current_depth: int, dir_index: DirIndex = None) -> Tuple[List[str], DirIndex]:
            # if the file exists, use it as default
            if DirIndex.dir_cache_exists(str(path)) or dir_index is None:
                dir_index = DirIndex.load_from_dir_cache(str(path))

            if current_depth > depth:
                return [], dir_index

            dir_path = str(path)

            items = []
            directories = []
            files = []
            # sort what ever files
            sorted_items = sorted(path.iterdir())

            for item in sorted_items:
                absolute_item = str(item)
                parsed_item = absolute_item
                relative_item = item.name
                if not absolute:
                    # remove prefix.
                    parsed_item = relative_item
                # ignore the dir_index file
                if dir_index.is_cache_file(parsed_item):
                    continue

                if item.is_dir() and list_dir and not self._match_pattern(item, self._ignores):
                    sub_directories_lines, sub_dir_index = _list_dir(item, current_depth + 1)
                    _summary = sub_dir_index.summary
                    _summary = " : " + _summary if summary and _summary else ""
                    if formated:
                        line = ' ' * current_depth * 2 + f"+ {parsed_item.strip('/')}/" + _summary
                    else:
                        line = parsed_item.rstrip('/') + '/' + _summary
                    directories.append(line)
                    directories.extend(sub_directories_lines)
                    dir_index.add_dir(relative_item, sub_dir_index.model_dump(exclude_defaults=True))
                elif item.is_file() and list_file and item.match(pattern) and not self._match_pattern(item, ignores):
                    _summary = dir_index.get_file_summary(relative_item)
                    _summary = " : " + _summary if summary and _summary else ""
                    if formated:
                        line = ' ' * current_depth * 2 + f"- {parsed_item.strip('/')}" + _summary
                    else:
                        line = parsed_item + _summary
                    dir_index.add_file(FileInfo(filename=relative_item), False)
                    files.append(line)
            items.extend(directories)
            items.extend(files)
            return items, dir_index

        items, self_dir_index = _list_dir(self._dir_path, 0)
        self._dir_index = self_dir_index
        return items

    @classmethod
    def _match_pattern(cls, path: Path, patterns: Optional[List[str]] = None) -> bool:
        if patterns is None:
            return False
        for pattern in patterns:
            if path.match(pattern):
                return True
        return False


# generated FileEditorImpl by ModuleEditThought (model is gpt-4o):
#
# if __name__ == "__main__":
#     from ghostos.thoughts.module_editor import new_pymodule_editor_thought
#     from ghostos.prototypes.console import demo_console_app
#
#     demo_console_app.run_thought(
#         new_pymodule_editor_thought(__name__),
#         instruction="please create FileEditorImpl class, receive a filepath as __init__ argument.",
#     )
# fixed the line number prefix alignment.

# generated DirectoryEditorImpl by ModuleEditThought (model is gpt-4o):
# if __name__ == "__main__":
#     from ghostos.thoughts.module_editor import new_pymodule_editor_thought
#     from ghostos.prototypes.console import demo_console_app
#
#     demo_console_app.run_thought(
#         new_pymodule_editor_thought(__name__),
#         instruction="""please create implementation of DirectoryEditor class,
# __init__ func receive a directory path argument.
# notice the absolute path must be sub path of the directory.
# relative path maybe use "../.." to escape this rule.
# """,
#     )

# if __name__ == "__main__":
#     from os.path import dirname
#
#     dir_editor = DirectoryEditorImpl(dirname(__file__))
#     print("\n".join(dir_editor.list(depth=2, formated=False)))

if __name__ == "__main__":
    from os.path import dirname

    dir_editor = DirectoryEditorImpl(dirname(dirname(__file__)), cache=True)
    dir_editor.edit_file(__file__).summarize(
        "defines FileEditor and DirectoryEditor abstract class with implementations")
    file_path = "libraries/arxiv_search.py"
    print("\n".join(dir_editor.list(depth=3, formated=True)))
    file_editor = dir_editor.edit_file(file_path)
    _content = file_editor.read()
    print(_content)
