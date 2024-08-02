from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class Descriptive(ABC):

    @abstractmethod
    def get_description(self) -> str:
        pass


class Identifier(BaseModel, Descriptive):
    id: str = Field(default="", description="Unique identifier")
    name: str = Field(default="", description="Name of the object")
    description: str = Field(default="", description="Description of the object")

    def get_description(self) -> str:
        return self.desc


class Identifiable(ABC):
    """
    描述一个可识别的对象.
    """

    @abstractmethod
    def identifier(self) -> Identifier:
        pass
