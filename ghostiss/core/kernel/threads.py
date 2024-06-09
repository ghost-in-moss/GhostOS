from abc import ABC, abstractmethod
from typing import Optional


class Thread(ABC):
    id: str


class Threads(ABC):

    @abstractmethod
    def get_thread(self, thread_id: str) -> Optional[Thread]:
        pass

    @abstractmethod
    def update_thread(self, thread: Thread) -> None:
        pass
