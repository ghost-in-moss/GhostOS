import inspect
from typing import Callable, Optional, Any, Type
from ghostos.core.moss.prompts import set_prompter, set_class_prompter
from ghostos.core.moss.utils import (
    get_callable_definition, make_class_prompt,
    strip_source_indent,
)

__all__ = [
    'cls_source_code', 'cls_definition',
    'definition', 'source_code',
]

DECORATOR = Callable[[Any], Any]
FUNC_DECORATOR = Callable[[Callable], Callable]
CLASS_DECORATOR = Callable[[Any], Any]


def cls_source_code(*, force: bool = False, doc: Optional[str] = None) -> DECORATOR:
    """
    decorator that add source code as prompt to the class
    :param force: if force true, add prompt event the prompter exists in target
    :param doc: docstring that shall replace the source code's docstring
    """

    def decorator(cls: Type) -> Type:
        def prompter():
            source = inspect.getsource(cls)
            source = strip_source_indent(source)
            return source

        set_class_prompter(cls, prompter, force)
        return cls

    return decorator


def source_code(*, force: bool = False) -> DECORATOR:
    """
    decorator that add source code as prompt to the function
    :param force: if force true, add prompt event the prompter exists in target
    """

    def decorator(fn: Callable) -> Callable:
        if not (inspect.isfunction(fn) or inspect.ismethod(fn)):
            raise AttributeError(f"fn '{fn}' has to be a function or method")

        def prompter():
            source = inspect.getsource(fn)
            source = strip_source_indent(source)
            return source

        set_prompter(fn, prompter, force)
        return fn

    return decorator


def definition(*, doc: Optional[str] = None, force: bool = False) -> FUNC_DECORATOR:
    """
    decorator that add definition only as prompt to the target func
    :param doc: if given, replace the docstring of the definition
    :param force: if force true, add prompt event the prompter exists in target
    """

    def decorator(fn):
        if inspect.isfunction(fn) or inspect.ismethod(fn):
            def prompter() -> str:
                prompt = get_callable_definition(fn, doc=doc)
                return prompt

            set_prompter(fn, prompter, force)
        else:
            raise AttributeError(f"fn '{fn}' has to be a function or method")
        return fn

    return decorator


def cls_definition(*, doc: Optional[str] = None, force: bool = False) -> CLASS_DECORATOR:
    """
    decorator that add definition only as prompt to the target class
    """

    def wrapper(cls):
        if not inspect.isclass(cls):
            raise AttributeError(f"cls '{cls}' is not a class")

        def prompter() -> str:
            source = inspect.getsource(cls)
            prompt = make_class_prompt(source=source, doc=doc)
            return prompt

        set_class_prompter(cls, prompter, force)
        return cls

    return wrapper
