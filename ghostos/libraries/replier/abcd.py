from abc import ABC, abstractmethod
from ghostos.abcd import Operator


# default session replier that could be executed in the MOSS protocol code

class Replier(ABC):
    """
    can send messages in the MOSS executor
    """

    @abstractmethod
    def wait_for(self, text: str) -> Operator:
        """
        say something and wait for the reply
        """
        pass
