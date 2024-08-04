from typing import Any
from abc import ABC, abstractmethod
from ghostiss.container import Container


class Reflection(ABC):

    @abstractmethod
    def value(self) -> Any:
        pass

    @abstractmethod
    def prompt(self, name: str) -> str:
        pass


class InContextReflection(Reflection):

    def value(self) -> Any:
        raise NotImplementedError("InContextReflection.value is not implemented, use factory instead")

    def factory(self, container: Container) -> Any:
        pass
