from typing import Callable, Optional, List, Generic, TypeVar, Union, Type, Any
from abc import ABC, abstractmethod
from ghostiss.moss2.prompts import PROMPT_MAGIC_ATTR

T = TypeVar('T')


class Decorator(Generic[T], ABC):

    @abstractmethod
    def prompt(self, value: T) -> str:
        pass

    def __call__(self, value: T) -> T:
        def prompt() -> str:
            return self.prompt(value)

        setattr(value, PROMPT_MAGIC_ATTR, prompt)
        return value


class WithPrompt(Decorator):

    def __init__(self, prompt: str):
        self.__prompt = prompt

    def prompt(self, value: Any) -> str:
        return self.__prompt


with_prompt = WithPrompt
"""snake case decorator name"""


def class_prompt(
        alias: Optional[str] = None,
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None,
        doc: Optional[str] = None,
):
    """
    decorator for a class to define prompt to it.
    add __moss_prompt__: Reflection to the class.

    :param alias: rename the class to this alias.
    :param includes: list of attr names that should be included in the prompt.
    :param excludes: list of attr names that should be excluded from the prompt.
    :param doc: docstring for the class that replace the origin one.
    """
    pass


def caller_prompt(
        alias: Optional[str] = None,
        doc: Optional[str] = None,
):
    """
    decorator for a callable to define prompt to it.
    add __moss_prompt__: Reflection to the callable object.

    :param
    """
