from abc import ABC, abstractmethod
from typing import Optional, Type
from ghostiss.container import Container, Provider, CONTRACT
from ghostiss.core.runtime.llms import LLMs
from ghostiss.core.runtime.threads import Threads
from ghostiss.core.runtime.tasks import Tasks
from ghostiss.core.runtime.processes import Processes

__all__ = [
    'Runtime', 'BasicRuntime', 'BasicRuntimeProvider'
]


class Runtime(ABC):

    @property
    @abstractmethod
    def processes(self) -> "Processes":
        pass

    @property
    @abstractmethod
    def llms(self) -> "LLMs":
        pass

    @property
    @abstractmethod
    def threads(self) -> "Threads":
        pass

    @property
    @abstractmethod
    def tasks(self) -> "Tasks":
        pass


class BasicRuntime(Runtime):

    def __init__(self, container: Container):
        self.container = container

    @property
    def processes(self) -> Processes:
        return self.container.force_fetch(Processes)

    @property
    def llms(self) -> "LLMs":
        return self.container.force_fetch(LLMs)

    @property
    def threads(self) -> "Threads":
        return self.container.force_fetch(Threads)

    @property
    def tasks(self) -> "Tasks":
        return self.container.force_fetch(Tasks)


class BasicRuntimeProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[CONTRACT]:
        return Runtime

    def factory(self, con: Container) -> Optional[CONTRACT]:
        return BasicRuntime(con)
