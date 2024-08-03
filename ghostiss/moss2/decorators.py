from typing import Callable, Optional, List as L


def class_prompt(
        alias: Optional[str] = None,
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None,
        doc: Optional[str] = None,
        prompt: Optional[str] = None,
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
