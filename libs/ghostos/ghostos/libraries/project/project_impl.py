from typing import Union, Optional
from typing_extensions import Self

from ghostos.abcd import Operator, Session
from ghostos.libraries.project.abcd import ProjectManager
from ghostos.libraries.terminal import Terminal
from ghostos.libraries.project.directory_impl import DirectoryImpl, FileImpl
from pydantic import BaseModel, Field
from ghostos_common.helpers import generate_import_path
from ghostos_common.prompter import PromptObjectModel, TextPOM
from ghostos_moss import Injection, MossRuntime
from ghostos_container import Container, Provider
import pathlib
import os


class ProjectData(BaseModel):
    root_dir: str = Field(description="Root path")
    working_dir: str = Field(description="Working directory")
    editing_file: Union[str, None] = Field(default=None, description="Editing file")


class ProjectManagerImpl(ProjectManager, PromptObjectModel, Injection):

    def __init__(
            self,
            root_dir: pathlib.Path,
            session: Session,
            working_on: str = None,
    ):
        self._session = session
        self._session_key = generate_import_path(ProjectManager)
        working_dir = root_dir.absolute()
        if working_on:
            working_dir = root_dir.joinpath(working_on)
        data = ProjectData(root_dir=str(root_dir.absolute()), working_dir=str(working_dir.absolute()))
        if self._session_key in session.state:
            _data = session.state[self._session_key]
            if isinstance(_data, ProjectData):
                data = _data
        self._data = data
        self.root: DirectoryImpl = DirectoryImpl(
            path=pathlib.Path(self._data.root_dir),
        )
        self.add_child(TextPOM(
            title="Root Directory Info",
            content=self.root.full_context(),
        ))
        working_path = pathlib.Path(self._data.working_dir)
        try:
            working_path.relative_to(root_dir)
        except ValueError:
            working_path = root_dir
        self.working: DirectoryImpl = DirectoryImpl(
            working_path,
            ignores=None,
            relative=str(working_path.relative_to(root_dir)),
        )
        if self._data.working_dir != self._data.root_dir:
            self.add_child(TextPOM(
                title="Working Directory Info",
                content=self.root.full_context(),
            ))

        self.editing: Union[FileImpl, None] = None
        if self._data.editing_file:
            self._set_editing(self._data.editing_file)

    def _set_editing(self, filename: str):
        filepath = self.working.path.joinpath(filename)
        filepath.relative_to(self.working.path)
        file_dev_ctx = self.working.dev_contexts().get(filename)
        if file_dev_ctx is None:
            filename = self._data.editing_file
            file_dev_ctx = self.working.new_dev_context(filename, f"file dev context on {filename}")
        self.editing = FileImpl(
            filepath,
            dev_ctx=file_dev_ctx,
        )

    def work_on(self, dir_path: str) -> Operator:
        self.working = self.root.subdir(dir_path)
        self._data.working_dir = str(self.working.path.absolute())
        self._data.editing_file = None
        return self._session.mindflow().think()

    def edit(self, file_path: str) -> Operator:
        self._set_editing(file_path)
        return self._session.mindflow().think()

    def terminal(self, *commands: str) -> Operator:
        terminal = self._session.container.force_fetch(Terminal)
        try:
            r = terminal.exec(*commands)
            return self._session.mindflow().think(
                f"exit_code: {r.exit_code}\n<stdout>{r.stdout}</stdout>\n<stderr>{r.stderr}</stderr>"
            )
        except Exception as e:
            return self._session.mindflow().error(f"Error occurs when executing terminal command: {e}")

    def self_prompt(self, container: Container) -> str:
        return "project manager information are:"

    def get_title(self) -> str:
        return "Project Manager Instance"

    def on_inject(self, runtime: MossRuntime, property_name: str) -> Self:
        return self

    def on_destroy(self) -> None:
        self.working.save_dev_contexts()
        self.root.save_dev_contexts()
        self._session.state[self._session_key] = self._data


class ProjectManagerProvider(Provider[ProjectManager]):

    def __init__(self, working_dir: str = None):
        self._working_dir = working_dir

    def singleton(self) -> bool:
        return False

    def inheritable(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[ProjectManager]:
        session = con.force_fetch(Session)
        root_path = pathlib.Path(os.getcwd())
        pr = ProjectManagerImpl(root_path, session, self._working_dir)
        return pr
