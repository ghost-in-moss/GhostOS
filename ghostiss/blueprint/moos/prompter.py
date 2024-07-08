from abc import ABC, abstractmethod
from typing import Any, Optional


class Prompter(ABC):

    @abstractmethod
    def prompt(self) -> str:
        pass


class AttrPrompter(Prompter):
    """
    # from xxx import yyy
    # implements xxx, xxx
    foo: Foo = bar
    \""" doc\"""
    """

    def __init__(
            self, *,
            name: str,
            typehint: Optional[str] = None,
            doc: Optional[str] = None,
    ):
        self.name = name
        self.typehint = typehint
        self.doc = doc

    def prompt(self) -> str:
        template = self.__doc__
        name = self.name
        typehint = ""
        if self.typehint is not None:
            typehint = f": {self.typehint}"
        doc = ""
        if self.doc is not None:
            doc = self.doc.replace('"""', '\\"""')
            doc = f'\n"""\n{doc}\n"""\n'
        return template.format(name=name, typehint=typehint, doc=doc)


class MethodPrompter(Prompter):

    def __init__(
            self, *,
    ):


class ClassPrompter(Prompter):
    pass
