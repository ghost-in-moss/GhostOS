from abc import ABC, abstractmethod
import openai

openai.beta.threads.create()


class Process(ABC):
    """

    """


class Runtime(ABC):

    @abstractmethod
    def process(self) -> Process:
        pass
