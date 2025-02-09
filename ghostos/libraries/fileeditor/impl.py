from typing import ClassVar, Dict
from ghostos.libraries.fileeditor.abcd import FileEditor, DirectoryEditor
from pydantic import BaseModel, Field
from ghostos.helpers import yaml_pretty_dump
from pathlib import Path
import os
import yaml


class FileInfo(BaseModel):
    summary: str = Field(
        default="",
        description="summary of the file or the directory",
    )
    filename: str = Field(description="the basename of the file")


class DirIndex(BaseModel):
    DIRECTORY_INDEX_FILE: ClassVar[str] = ".DIR_INFO.yml"

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

    def __init__(self, filename: str):
        self.filename = filename
        if not os.path.exists(self.filename):
            raise FileNotFoundError(f'File "{self.filename}" does not exist')

    def abspath(self) -> str:
        return self.filename

    def summarize(self, summary: str) -> None:
        _dir = os.path.dirname(self.filename)
        index = DirIndex.load_from_dir_cache(_dir)
        filename = Path(self.filename).name
        index.set_file_summary(filename, summary)
        index.save_to_dir_cache(_dir)

    def read(self, show_line_num: bool = False, start_line: int = 0, end_line: int = -1) -> str:
        with open(self.filename, 'r') as file:
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
        with open(self.filename, 'r') as file:
            lines = file.readlines()
        if end_line < 0:
            end_line = len(lines) + end_line
        original = ''.join(lines[start_line:end_line + 1])
        lines[start_line:end_line + 1] = replacement.splitlines(keepends=True)
        with open(self.filename, 'w') as file:
            file.writelines(lines)
        return original

    def replace(self, origin: str, replace: str, count: int = -1) -> None:
        with open(self.filename, 'r') as file:
            content = file.read()
        new_content = content.replace(origin, replace, count)
        with open(self.filename, 'w') as file:
            file.write(new_content)

    def append(self, content: str) -> None:
        with open(self.filename, 'a') as file:
            file.write(content)

    def insert(self, content: str, position: int) -> None:
        with open(self.filename, 'r') as file:
            lines = file.readlines()
        lines.insert(position, content + '\n')
        with open(self.filename, 'w') as file:
            file.writelines(lines)


DEFAULT_IGNORES = ['__pycache__', '*.pyc', '*.pyo', 'venv', '.idea', r'^\.', '*.log']
