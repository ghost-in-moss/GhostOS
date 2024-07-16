from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from ghostiss.container import Container

if TYPE_CHECKING:
    from ghostiss.core.runtime.llms import LLMs
    from ghostiss.core.runtime.threads import Threads
    from ghostiss.core.runtime.runs import Runs
    from ghostiss.core.runtime.queues import Queues


class Runtime(ABC):

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
