from abc import ABC, abstractmethod
from typing import Type, Dict
from types import ModuleType

__all__ = [
    'is_magic_prompter', 'MagicPrompter', 'replace_magic_prompter',
    '__is_instance__', '__is_subclass__',
]


def __is_instance__(type_: Type):
    """
    list all the attrs of current module which are instances of type_
    """
    return _IsTypePrompter(type_)


def __is_subclass__(type_: Type):
    """
    list all the attrs of current module which are subclasses of type_
    """
    return _IsSubclassPrompter(type_)


class MagicPrompter(ABC):

    @abstractmethod
    def __moss_magic_prompt__(self, compiled: ModuleType) -> str:
        pass


def is_magic_prompter(value) -> bool:
    return isinstance(value, MagicPrompter)


def replace_magic_prompter(module: ModuleType) -> Dict[str, str]:
    replaced = {}
    for attr, value in module.__dict__.items():
        if isinstance(value, MagicPrompter):
            replaced[attr] = value.__moss_magic_prompt__(module)
    module.__dict__.update(replaced)
    return replaced


class _IsTypePrompter(MagicPrompter):

    def __init__(self, _type: type):
        self._type = _type

    def __moss_magic_prompt__(self, compiled: ModuleType) -> str:
        matched = []
        for name, value in compiled.__dict__.items():
            if name.startswith("_"):
                continue
            if isinstance(value, self._type):
                matched.append(name)

        return f'''
the attrs which is instance of {self._type} are:{", ".join(matched)}
'''


class _IsSubclassPrompter(MagicPrompter):

    def __init__(self, parent: type):
        self._parent = parent

    def __moss_magic_prompt__(self, compiled: ModuleType) -> str:
        matched = []
        for name, value in compiled.__dict__.items():
            if name.startswith("_"):
                continue
            if isinstance(value, type) and issubclass(value, self._parent):
                matched.append(name)
        return f'''
the attrs which is subclass of {self._parent} are: {", ".join(matched)}
'''
