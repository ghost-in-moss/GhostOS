import inspect
from typing import Callable, Optional, Any, Type
from ghostos.prompter import set_prompt, set_class_prompt
from ghostos.core.moss.utils import (
    get_callable_definition, make_class_prompt,
    strip_source_indent,
)

__all__ = [
    'cls_source_code', 'cls_definition',
    'definition', 'source_code',
    'no_prompt',
]

DECORATOR = Callable[[Any], Any]
FUNC_DECORATOR = Callable[[Callable], Callable]
CLASS_DECORATOR = Callable[[Any], Any]


def no_prompt(func: Callable) -> Callable:
    """
    set empty prompt to a func
    """
    func.__prompt__ = ""
    return func


no_prompt.__prompt__ = ""


def cls_source_code(*, force: bool = False) -> DECORATOR:
    """
    decorator that add source code as prompt to the class
    :param force: if force true, add prompt event the prompter exists in target
    """

    def decorator(cls: Type) -> Type:
        def prompter():
            source = inspect.getsource(cls)
            source = strip_source_indent(source)
            return source

        set_class_prompt(cls, prompter, force)
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

        def prompter() -> str:
            source = inspect.getsource(fn)
            source = strip_source_indent(source)
            return source

        set_prompt(fn, prompter, force)
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

            set_prompt(fn, prompter, force)
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

        set_class_prompt(cls, prompter, force)
        return cls

    return wrapper


def cls_outline(*, doc: Optional[str] = None, force: bool = False) -> CLASS_DECORATOR:
    """
    decorator that add outline as prompt to the class
    """

    def wrapper(cls: Type):
        if not inspect.isclass(cls):
            raise AttributeError(f"cls '{cls}' is not a class")

        def prompter() -> str:
            source = inspect.getsource(cls)
            # get definition, docstring, exported methods(include docstring) of the class
            # 1. get definition
            class_definition = make_class_prompt(source=source, doc=doc)
            # del the pass (last line) in the class definition
            class_definition = class_definition.split('\n')
            class_definition = class_definition[:-1]
            class_definition = '\n'.join(class_definition)

            # 2. get docstring
            class_docstring = inspect.getdoc(cls) or ""
            # 3. get exported methods(include docstring)
            methods = []
            for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                if not name.startswith('_') or name in ['__init__']:
                    method_source = inspect.getsource(method).split('\n')
                    method_code = []
                    in_docstring = False
                    encountered_def = False

                    for line in method_source:
                        if not encountered_def:
                            method_code.append(line)
                            stripped_line = line.strip()
                            if stripped_line.startswith("def"):
                                encountered_def = True
                        else:
                            stripped_line = line.strip()
                            if in_docstring:
                                method_code.append(line)
                                if stripped_line.startswith('"""') or stripped_line.startswith("'''"):
                                    # end the docstring
                                    in_docstring = False
                                    break
                            else:
                                if len(stripped_line) > 0:
                                    if stripped_line.startswith('"""') or stripped_line.startswith("'''"):
                                        # start the docstring
                                        in_docstring = True
                                        method_code.append(line)
                                    else:  # encounter the first not-docstring line
                                        break
                    method_code = '\n'.join(method_code)
                    methods.append('\n' + method_code)
            methods_prompt = "\n".join(methods)
            # 4. combine them
            combined_prompt = f"{class_definition}\n    '''\n    {class_docstring}\n    ''' \n" + methods_prompt
            # 5. return
            return combined_prompt

        set_class_prompt(cls, prompter, force)
        return cls

    return wrapper
