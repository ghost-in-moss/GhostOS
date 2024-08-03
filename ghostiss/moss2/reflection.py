from typing import Any, Optional, Union, Type
from abc import ABC, abstractmethod


class Reflection(ABC):
    """
    reflect a value to moss context.
    """

    @abstractmethod
    def name(self) -> str:
        """
        value's name in current moss context
        """
        pass

    @abstractmethod
    def value(self) -> Any:
        """
        the value
        """
        pass

    @abstractmethod
    def prompt(self) -> str:
        """
        the prompt of the value in moss prompt.
        """
        pass

    @abstractmethod
    def generate_prompt(self) -> str:
        """
        regenerate prompt of the value in current moss context.
        """
        pass

    @abstractmethod
    def from_module(self) -> Optional[str]:
        """
        modulename where the value is imported from.
        """
        pass

    @abstractmethod
    def from_module_attr(self) -> Optional[str]:
        """
        the specific attribute name in the module where the value is imported from.
        """
        pass

    @abstractmethod
    def typehint(self) -> Union[Type, str]:
        """
        Type of the value. if value is a Type, return itself.
        :return: the real Type or a string that describes the type.
        """


class AttrReflection(Reflection, ABC):
    pass


class CallableReflection(Reflection, ABC):
    pass


class TypeReflection(Reflection, ABC):
    pass


class Attr(AttrReflection):
    pass


class DictAttr(AttrReflection):
    pass


class Typing(AttrReflection):
    pass


class Interface(TypeReflection):
    pass


class ClassStub(TypeReflection):
    pass
