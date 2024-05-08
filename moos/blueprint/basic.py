from typing import Any, Type
from abc import ABC, abstractmethod
import inspect


class PromptAbleType(ABC):
    """
    any class that prompt-able for llm
    """

    @classmethod
    @abstractmethod
    def abstract_prompt(cls) -> str:
        pass


class PromptAbleObject(ABC):

    @abstractmethod
    def instance_prompt(self) -> str:
        """
        additional prompt of the object
        """
        pass


def get_prompt_by_source(cls: Any) -> str:
    """
    use source code as prompt
    """
    # todo: 随便乱写的, 需要根据实际使用情况修改.
    return inspect.getsource(cls)
