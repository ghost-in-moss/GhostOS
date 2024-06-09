from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from ghostiss.container import Container

if TYPE_CHECKING:
    from ghostiss.core.kernel.llms import LLMs
    from ghostiss.core.kernel.threads import Threads
    from ghostiss.core.kernel.runs import Runs
    from ghostiss.core.kernel.queues import Queues
    from ghostiss.core.kernel.python import Python


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
