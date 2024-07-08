from typing import Any, Optional, List, Tuple, Callable
from abc import ABC, abstractmethod
from ghostiss.blueprint.moos.helpers import (
    get_module_name,
    get_callable_name, get_callable_definition,
)


class Var(ABC):

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def import_from(self) -> Optional[Tuple[str, str]]:
        pass

    @abstractmethod
    def value(self) -> Any:
        pass

    @abstractmethod
    def prompt(self) -> str:
        pass


class AnyVar(Var):

    def __init__(
            self, *,
            name: str,
            value: Any,
            prompt: str,
            import_from: Optional[Tuple[str, str]] = None,
    ):
        self._name = name
        self._value = value
        self._prompt = prompt
        self._import_from = import_from

    def name(self) -> str:
        return self._name

    def import_from(self) -> Optional[Tuple[str, str]]:
        return self._import_from

    def value(self) -> Any:
        return self._value

    def prompt(self) -> str:
        return self._prompt


class CallerVar(Var):

    def __init__(
            self, *,
            caller: Callable,
            alias: Optional[str] = None,
            doc: Optional[str] = None,
            import_from: Optional[Tuple[str, str]] = None,
            prompt: Optional[str] = None,
    ):
        self._caller = caller
        self._alias = alias
        self._doc = doc
        self._import_from = import_from
        self._prompt = prompt

    def name(self) -> str:
        if self._alias:
            return self._alias
        return self._caller.__name__

    def import_from(self) -> Optional[Tuple[str, str]]:
        if self._import_from:
            return self._import_from
        module = get_module_name(self._caller)
        if module:
            return module, get_callable_name(self._caller)
        # None means local defined.
        return None

    def value(self) -> Callable:
        return self._caller

    def prompt(self) -> str:
        if self._prompt:
            return self._prompt
        return get_callable_definition(self._caller, doc=self._doc, method_name=self._alias)


class AttrVar(Var):
    def __init__(
            self, *,
            name: str,
            value: Any,
            implements: Optional[type] = None,
            doc: Optional[str] = None,
    ):
        self._name = name
        self._value = value
        self._implements = implements
        self._doc = doc


class DictAttrVar(AttrVar):

class TypeVar(Var):

    def __init__(
            self,
            *,
            typ: type,
            prompt: str,
    ):
        self._type = typ
        self._prompt = prompt

    def value(self) -> type:
        return self._type

    def prompt(self) -> str:
        return self._prompt


class ClassVar(TypeVar):

    def __init__(
            self, *,
            typ: type,
            alias: Optional[str] = None,
            doc: Optional[str] = None,
            constructor: bool = False,
            methods: Optional[List[str]] = None,
            attrs: Optional[List[str]] = None,
    ):
        super().__init__(typ=typ, prompt=prompt)


class AbcClassVar(TypeVar):
    pass


class InterfaceVar(TypeVar):
    pass


class LocalsVar(Var):

    def value(self) -> Any:
        pass

    def add_type(self):
        pass

    def prompt(self) -> str:
        pass
