from abc import ABC, abstractmethod
from ghostos.contracts.storage import FileStorage


class Workspace(ABC):
    """
    workspace that ghost can work on
    """

    @abstractmethod
    def root(self) -> FileStorage:
        """
        the root storage of the workspace
        """
        pass

    @abstractmethod
    def runtime(self) -> FileStorage:
        """
        runtime that save data by filesystem
        """
        pass

    @abstractmethod
    def configs(self) -> FileStorage:
        """
        config path that configs located
        """
        pass

    @abstractmethod
    def source(self) -> FileStorage:
        """
        source code path
        """
        pass
