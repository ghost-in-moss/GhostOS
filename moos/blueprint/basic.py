from typing import Any, Type
from abc import ABC, abstractmethod
import inspect


class PromptAbleClass(ABC):
    """
    any class that prompt-able for llm
    """

    @classmethod
    @abstractmethod
    def abstract_prompt(cls) -> str:
        pass


class PromptAbleIns(ABC):

    @classmethod
    @abstractmethod
    def prompt_class(cls) -> Type[PromptAbleClass]:
        pass

    @abstractmethod
    def instance_prompt(self) -> str:
        pass


def class_source_prompt(cls: Any) -> str:
    """
    use source code as prompt
    """
    # todo: if is interface of a class, will raise TypeError. 合理否?
    return inspect.getsource(cls)
