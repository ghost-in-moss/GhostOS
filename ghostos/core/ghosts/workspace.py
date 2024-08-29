from abc import ABC, abstractmethod
from ghostos.contracts.storage import Storage


class Workspace(ABC):
    """
    workspace that ghost can work on
    """

    @abstractmethod
    def runtime(self) -> Storage:
        """
        runtime that save data by filesystem
        """
        pass

    @abstractmethod
    def configs(self) -> Storage:
        """
        config path that configs located
        """
        pass

    @abstractmethod
    def source(self) -> Storage:
        """
        source code path
        """
        pass
