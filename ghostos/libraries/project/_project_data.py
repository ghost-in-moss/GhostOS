from typing import Dict
from abc import ABC, abstractmethod
from ghostos.libraries.project.abcd import Project
from ghostos.contracts.logger import LoggerItf
from ghostos_common.helpers import yaml_pretty_dump
from pydantic import BaseModel, Field
from threading import Lock
from os.path import join, isdir, isfile, exists, abspath
import yaml


class PathNote(BaseModel):
    path: str = Field(description="relative path")
    desc: str = Field(default="")
    notes: Dict[str, str] = Field(default_factory=dict)


class ProjectData(BaseModel):
    config: Project.ProjectConfig = Field(
        default_factory=Project.ProjectConfig,
    )

    notes: Dict[str, PathNote] = Field(
        default_factory=dict
    )


class ProjectDataRepository(ABC):

    @abstractmethod
    def get_config(self) -> Project.ProjectConfig:
        pass

    @abstractmethod
    def save_config(self, config: Project.ProjectConfig) -> None:
        pass

    @abstractmethod
    def get_notes(self) -> Dict[str, PathNote]:
        pass

    @abstractmethod
    def save_note(self, note: PathNote) -> None:
        pass


class FileProjectDataRepository(ProjectDataRepository):
    PROJECT_DATA_FILENAME = ".ghostos_project.yml"

    def __init__(
            self,
            rootpath: str,
            logger: LoggerItf
    ):
        self.root = abspath(rootpath)
        if not exists(self.root) or not isdir(self.root):
            raise NotADirectoryError(f'{rootpath} does not exist')
        self._data = self._get_data()
        self._data_filename = join(self.root, self.PROJECT_DATA_FILENAME)
        self._mutex = Lock()
        self.logger = logger

    def _get_data(self) -> ProjectData:
        if not exists(self._data_filename):
            return ProjectData()
        with open(self._data_filename, "r") as f:
            content = f.read()
            try:
                data = yaml.safe_load(content)
                return ProjectData(**data)
            except Exception as e:
                self.logger.exception(e)
                return ProjectData()

    def _save_data(self) -> None:
        with self._mutex:
            saving = self._data.model_dump(exclude_defaults=True)
            content = yaml_pretty_dump(saving)
            with open(self._data_filename, "w") as f:
                f.write(content)

    def get_config(self) -> Project.ProjectConfig:
        return self._data

    def save_config(self, config: Project.ProjectConfig) -> None:
        self._data.config = config
        self._save_data()

    def get_notes(self) -> Dict[str, PathNote]:
        return self._data.notes

    def save_note(self, note: PathNote) -> None:
        self._data.notes[note.path] = note
        self._save_data()
