from abc import ABC, abstractmethod




class PromptAbleClass(ABC):

    @classmethod
    @abstractmethod
    def class_prompt(cls) -> str:
        pass
