from abc import ABC, abstractmethod
from typing import List, Type, Optional
from ghostiss.core.ghosts.libraries import Driver


class Shell(ABC):

    @abstractmethod
    def id(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def drivers(self) -> List[Type[object]]:
        pass

    @abstractmethod
    def get_driver(self, driver_type: Type[Driver]) -> Optional[Driver]:
        pass
