from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ghostiss.meta import MetaData

if TYPE_CHECKING:
    from ghostiss.interfaces.thoughts import Think, Mindset


class Ghost(ABC):

    @abstractmethod
    def id(self) -> str:
        pass

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def mindset(self) -> Mindset:
        pass

    @abstractmethod
    def root_thought(self) -> MetaData:
        pass
