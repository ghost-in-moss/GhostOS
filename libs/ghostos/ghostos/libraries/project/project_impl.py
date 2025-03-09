from typing import Optional

from ghostos.abcd import Operator, Session
from ghostos.libraries.project.abcd import ProjectManager
from ghostos.libraries.pyeditor import PyModuleEditor
from ghostos.libraries.terminal import Terminal
from ghostos.libraries.project.directory_impl import DirectoryImpl
from ghostos.libraries.pyeditor.simple_module_editor import SimplePyModuleEditor
from pydantic import BaseModel, Field
from ghostos_common.helpers import generate_import_path
from ghostos_common.prompter import PromptObjectModel, TextPOM
from ghostos_moss import Modules
from ghostos_container import Container, Provider
import pathlib


class ProjectData(BaseModel):
    root_dir: str = Field(description="Root path")
    working_dir: str = Field(description="Working directory")


class ProjectManagerImpl(ProjectManager, PromptObjectModel):

    def __init__(
            self,
            root_dir: pathlib.Path,
            session: Session,
            working_on: str = None,
    ):
        self._session = session
        self._session_key = generate_import_path(ProjectManager)
        working_dir = root_dir.absolute()
        editing_file: Optional[str] = None
        if working_on:
            working_obj = root_dir.joinpath(working_on).absolute()
            if not working_obj.is_dir():
                working_dir = working_obj.parent
                editing_file = str(working_obj.relative_to(working_dir))
            else:
                working_dir = working_obj

        data = ProjectData(
            root_dir=str(root_dir.absolute()),
            working_dir=str(working_dir.absolute()),
        )
        if self._session_key in session.state:
            _data = session.state[self._session_key]
            if isinstance(_data, ProjectData):
                data = _data
        self._data = data
        self.root: DirectoryImpl = DirectoryImpl(
            path=pathlib.Path(self._data.root_dir),
        )
        self.working: DirectoryImpl = DirectoryImpl(
            path=pathlib.Path(self._data.working_dir),
        )
        self.working.focus(editing_file)

        self.add_child(TextPOM(
            title="Root Directory Info",
            content=self.root.full_context(),
        ))

        if self._data.working_dir != self._data.root_dir:
            self.add_child(TextPOM(
                title="Working Directory Info",
                content=self.working.full_context(),
            ))
        else:
            self.add_child(TextPOM(
                title="Working Directory Info",
                content=f"working directory is the root directory",
            ))

    def _set_working_on(self, working_path: pathlib.Path):
        root_dir = self.root.path
        try:
            working_path.relative_to(root_dir)
        except ValueError:
            working_path = root_dir
        self.working: DirectoryImpl = DirectoryImpl(
            working_path,
            ignores=None,
        )

    def work_on(self, dir_path: str) -> Operator:
        dir_root = self.root.path
        if dir_path == '.' or dir_path == '~':
            dir_root = self.root.path
            dir_path = dir_path[1:]
        working_path = dir_root.joinpath(dir_path).absolute()
        working_path.relative_to(self.root.path)

        self.working = DirectoryImpl(working_path, self.root.get_ignores())
        self._data.working_dir = str(self.working.path.absolute())
        return self._session.mindflow().think()

    def edit_pymodule(self, modulename: str) -> PyModuleEditor:
        return SimplePyModuleEditor(modulename, "", self._session.container.force_fetch(Modules))

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


class ProjectManagerProvider(Provider[ProjectManager]):

    def __init__(
            self,
            root_dir: str,
            working_on: str = None,
    ):
        self.root_dir = root_dir
        self._working_on = working_on

    def singleton(self) -> bool:
        return False

    def inheritable(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[ProjectManager]:
        session = con.force_fetch(Session)
        root_path = pathlib.Path(self.root_dir).resolve().absolute()
        pr = ProjectManagerImpl(root_path, session, self._working_on)
        return pr
