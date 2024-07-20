from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class Descriptive(ABC):

    @abstractmethod
    def description(self) -> str:
        pass


class Identifier(BaseModel, Descriptive):
    id: str
    name: str
    desc: str

    def description(self) -> str:
        return self.desc


class Identifiable(ABC):
    """
    描述一个可识别的对象.
    """

    @abstractmethod
    def identifier(self) -> Identifier:
        pass
