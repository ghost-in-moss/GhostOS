from typing import List, Dict
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class ModuleInfo(BaseModel):
    name: str = Field(description="The name of the module.")
    file: str = Field(description="The file of the name")
    package: bool = Field(description="is package")
    interface: str = Field(description="The interface of the module.")
    imported: List[str] = Field(default_factory=list, description="The imported modules.")


class PyCodexGenerator(ABC):

    @abstractmethod
    def generate(self, root_module: str, ignore_error: bool = False) -> Dict[str, ModuleInfo]:
        pass

    @abstractmethod
    def dump_yaml(self, modules: Dict[str, ModuleInfo]) -> str:
        pass

    @abstractmethod
    def from_yaml(self, content: str) -> Dict[str, ModuleInfo]:
        pass
