from typing import Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import enum


class ImportType(str, enum.Enum):
    MODULE = 'module'
    FUNCTION = 'function'
    LIBRARY = 'library'
    CLASS = 'class'


class Imported(BaseModel):
    module: str
    name: Optional[str] = Field(default=None)
    alias: Optional[str] = Field(default=None)


class PyContext(BaseModel):
    pass


class PyRuntime(ABC):
    pass


class Interpreter(ABC):

    @abstractmethod
    def run(self):
        pass
