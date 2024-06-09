from abc import ABC, abstractmethod


class PromptAbleObject(ABC):

    @abstractmethod
    def prompt(self) -> str:
        pass


class PromptAbleClass(ABC):

    @classmethod
    @abstractmethod
    def class_prompt(cls) -> str:
        pass
