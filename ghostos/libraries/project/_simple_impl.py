from typing import Optional, Dict, Iterable, TypedDict, Tuple
from typing_extensions import Self

from ghostos_container import Container
from ghostos.contracts.logger import LoggerItf
from ghostos.libraries.project.abcd import Project
from ghostos.libraries.terminal import Terminal
from ghostos.libraries.project._project_data import FileProjectDataRepository, PathNote
from ghostos_moss import Injection, MossRuntime
from pathlib import Path
import os


class PathNode:

    def __init__(self, path: Path, depth: int = 0):
        self.path = path
        self.is_dir = path.is_dir()
        self.depth = depth

    @classmethod
    def from_filepath(cls, filepath: str) -> Self:
        return cls(Path(filepath))

    def ignored(self, patterns: Iterable[str]) -> bool:
        if self.path.is_file():
            return True
        for pattern in patterns:
            if self.path.match(pattern):
                return False
        return True

    def children(self, patterns: Iterable[str]) -> Iterable[Self]:
        if not self.path.is_dir():
            return []
        for p in self.path.iterdir():
            wrapped = PathNode(p, depth=self.depth + 1)
            if wrapped.ignored(patterns):
                continue
            yield wrapped

    def iter_nodes(self, patterns: Iterable[str], max_depth: int, limit: int) -> Iterable[Self]:
        if self.depth >= max_depth:
            return
        yield self
        limit -= 1
        if limit <= 0:
            return []

        for child in self.children(patterns):
            yield from child.iter_nodes(patterns, max_depth, limit)

    def markdown_item(self, desc: str = "") -> str:
        name = self.path.name
        mark = "+" if self.path.is_dir() else "-"
        content = f": {desc}" if desc else ""
        return ' ' * 2 * self.depth + f"{mark} {name}{content}"


class SimpleProjectManager(Project, Injection):

    def __init__(
            self,
            rootpath: str,
            terminal: Terminal,
            logger: LoggerItf,
    ):
        self.logger = logger
        rootpath = os.path.abspath(rootpath)
        self._rootpath = rootpath
        self._repository = FileProjectDataRepository(rootpath, logger)
        self.terminal = terminal
        self.config = self._repository.get_config()

    def save_note(self, relative_path: str, *, desc: str = None, notes: Dict[str, str] = None) -> bool:
        note = self._get_note(relative_path)
        if note is None:
            return False
        if desc:
            note.desc = desc
        if notes is not None:
            note.notes.update(notes)

        self._repository.save_note(note)
        return True

    def on_inject(self, runtime: MossRuntime, property_name: str) -> Self:
        return self

    def on_destroy(self) -> None:
        self._repository.save_config(self.config)

    def _get_note(self, relative_path: str) -> Optional[PathNote]:
        filename = self._get_abs_filepath(relative_path)
        if filename is None:
            return None

        relative = filename[len(self._rootpath):].rstrip(os.path.sep)
        note = self._repository.get_notes().get(relative)
        if note is None:
            note = PathNote(path=relative)
        return note

    def _get_relative_path(self, full_path: str) -> Optional[str]:
        if not full_path.startswith(self._rootpath):
            return None
        return full_path[len(self._rootpath):].rstrip(os.path.sep)

    def _get_abs_filepath(self, relative_path: str) -> Optional[str]:
        filename = os.path.abspath(os.path.join(self._rootpath, relative_path))
        if not os.path.exists(filename):
            return None
        if not filename.startswith(self._rootpath):
            return None
        return filename

    def get_note(self, relative_path: str) -> Tuple[str, Dict[str, str]]:
        note = self._get_note(relative_path)
        if note is None:
            return "", dict()
        return note.description, note.notes

    def list_paths(self, prefix: str = '', depth: int = 0, limit: int = 30) -> str:
        ignores = self.config.ignores

        if prefix:
            filepath = self._get_abs_filepath(prefix)
        else:
            relative = os.path.join(self._rootpath, prefix)
            filepath = self._get_abs_filepath(relative)

        if filepath is None:
            return ""

        markdown_lines = []
        current = PathNode(Path(filepath), 0)
        for node in current.iter_nodes(ignores, depth, limit):
            relative = self._get_relative_path(str(node.path))
            desc, notes = self.get_note(relative)
            line = node.markdown_item(desc)
            markdown_lines.append(line)

        return '\n'.join(markdown_lines)

    def read_file(self, filename: str) -> str:
        full_filename = self._get_abs_filepath(filename)
        if full_filename is None:
            raise FileNotFoundError(f"{filename} not found or not allowed in this project")
        with open(full_filename, 'r') as f:
            return f.read()

    def save_file(self, filename: str, content: str) -> None:
        full_filename = self._get_abs_filepath(filename)
        if full_filename is None:
            raise FileNotFoundError(f"{filename} not found or not allowed in this project")
        with open(full_filename, 'w') as f:
            f.write(content)

    def self_prompt(self, container: Container) -> str:
        return ""

    def get_title(self) -> str:
        return "ProjectManager context"
