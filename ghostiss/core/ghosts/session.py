from abc import ABC, abstractmethod

from ghostiss.core.runtime.processes import Process
from ghostiss.core.runtime.tasks import Task
from ghostiss.core.runtime.threads import Thread


class Session(ABC):

    @abstractmethod
    def process(self) -> Process:
        pass

    @abstractmethod
    def task(self) -> Task:
        pass

    @abstractmethod
    def thread(self) -> Thread:
        pass

    @abstractmethod
    def update_task(self, task: Task) -> None:
        pass

    @abstractmethod
    def update_thread(self, thread: Thread) -> None:
        pass

    @abstractmethod
    def finish(self) -> None:
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass
