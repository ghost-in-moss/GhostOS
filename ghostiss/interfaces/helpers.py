from abc import ABC, abstractmethod

class Helper(ABC):

    @abstractmethod
    def uuid(self) -> str:
        pass