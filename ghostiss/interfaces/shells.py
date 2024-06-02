from abc import ABC, abstractmethod
from ghostiss.messages import Messenger, MessageBuffer


class Shell(ABC):

    @abstractmethod
    def shell_id(self) -> str:
        pass

    @abstractmethod
    def shell_type(self) -> str:
        pass

    @abstractmethod
    def messenger(self) -> Messenger:
        pass
