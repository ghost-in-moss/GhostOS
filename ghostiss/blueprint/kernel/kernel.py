from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from ghostiss.container import Container

if TYPE_CHECKING:
    from ghostiss.blueprint.kernel.llms import LLMs
    from ghostiss.blueprint.kernel.threads import Threads
    from ghostiss.blueprint.kernel.runs import Runs
    from ghostiss.blueprint.kernel.queues import Queues
    from ghostiss.blueprint.python import Python


class Kernel(ABC):

    @property
    @abstractmethod
    def container(self) -> Container:
        pass

    @property
    @abstractmethod
    def python(self) -> Python:
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
    def runs(self) -> "Runs":
        pass

    @property
    @abstractmethod
    def queues(self) -> "Queues":
        pass
