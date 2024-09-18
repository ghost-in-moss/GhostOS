from typing import Optional, List
from abc import ABC, abstractmethod
from pathlib import Path


class DirectoryEditor(ABC):

    @abstractmethod
    def edit_file(self, relative_path: str, create_nx: bool = False) -> "FileEditor":
        """
        create FileEditor to edit file
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
            ignores: Optional[str] = None,
            formated: bool = True,
    ) -> List[str]:
        """
        list the directories and files in the current directory
        :param depth: the recursive directory depth. 0 means current directory only
        :param list_dir: if True, list the directories. if False, will not list recursively
        :param list_file: if True, list the files.
        :param pattern: regex pattern to filter files, not directories.
        :param ignores: regex pattern to ignore files. None means default ignore rules.
        :param formated: if True, list result will be formatted as a  list tree in markdown,
               '+' means directory, '-' means file. If False, display raw file name
        :return: list of the files and directories. you can use "\n".join(listed) to display them.
        """
        pass


class FileEditor(ABC):
    """
    useful to edit a certain file.
    """

    @abstractmethod
    def filepath(self) -> str:
        """
        the full path of the current editing file
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


class FileEditorImpl(FileEditor):
    def __init__(self, filepath: str):
        self._filepath = filepath

    def filepath(self) -> str:
        return self._filepath

    def read(self, show_line_num: bool = False, start_line: int = 0, end_line: int = -1) -> str:
        with open(self._filepath, 'r') as file:
            lines = file.readlines()
        if end_line < 0:
            end_line = len(lines) + end_line
        lines = lines[start_line:end_line + 1]

        if not show_line_num:
            return '\n'.join(lines)
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


class DirectoryEditorImpl(DirectoryEditor):
    def __init__(self, dir_path: str, ignores: Optional[List[str]] = None):
        self._ignores = ignores if ignores is not None else ['__pycache__', '*.pyc', '*.pyo', 'venv']
        self._dir_path = Path(dir_path)
        if not self._dir_path.is_dir():
            raise FileNotFoundError(f"Directory {dir_path} does not exist")

    def edit_file(self, relative_path: str, create_nx: bool = False) -> FileEditor:
        file_path = self._dir_path / relative_path
        if not file_path.exists():
            if create_nx:
                file_path.touch()
            else:
                raise FileNotFoundError(f"File {relative_path} not found in {self._dir_path}")
        return FileEditorImpl(str(file_path))

    def edit_dir(self, relative_dir: str, create_nx: bool = True) -> DirectoryEditor:
        dir_path = self._dir_path / relative_dir
        if not dir_path.exists():
            if create_nx:
                dir_path.mkdir(parents=True)
            else:
                raise FileNotFoundError(f"Directory {relative_dir} not found in {self._dir_path}")
        return DirectoryEditorImpl(str(dir_path))

    def list(
            self, *,
            depth: int = 0,
            list_dir: bool = True,
            list_file: bool = True,
            pattern: str = "*",
            ignores: Optional[List[str]] = None,
            formated: bool = True,
    ) -> List[str]:
        ignores = ignores or self._ignores

        def _list_dir(path: Path, current_depth: int):
            if current_depth > depth:
                return []
            items = []
            directories = []
            files = []
            sorted_items = sorted(path.iterdir())
            for item in sorted_items:
                path_item = str(item)
                if formated:
                    path_item = path_item.replace(str(path), "")
                if item.is_dir() and list_dir and not self._match_pattern(item, self._ignores):
                    if formated:
                        line = ' ' * current_depth * 2 + f"+ {path_item.strip('/')}/"
                    else:
                        line = str(item).rstrip('/') + '/'
                    directories.append(line)
                    directories.extend(_list_dir(item, current_depth + 1))
                elif item.is_file() and list_file and item.match(pattern) and not self._match_pattern(item, ignores):
                    if formated:
                        line = ' ' * current_depth * 2 + f"- {path_item.strip('/')}"
                    else:
                        line = str(item)
                    files.append(line)
            items.extend(directories)
            items.extend(files)
            return items

        items = _list_dir(self._dir_path, 0)
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

if __name__ == "__main__":
    from os.path import dirname

    dir_editor = DirectoryEditorImpl(dirname(dirname(__file__)))
    print("\n".join(dir_editor.list(depth=3, formated=False)))
