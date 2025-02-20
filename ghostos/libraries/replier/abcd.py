from abc import ABC, abstractmethod
from ghostos.abcd import Operator


# default session replier that could be executed in the MOSS protocol code

class Replier(ABC):
    """
    can send messages in the MOSS executor.
    not required, just you don't need to repeat a string by your generated tokens, but send the string value directly.
    useless when you don't run MOSS.
    """

    @abstractmethod
    def wait_for(self, text: str) -> Operator:
        """
        say something and wait for the reply
        """
        pass
