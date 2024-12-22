from typing import TypeVar, Union, Callable
from types import ModuleType

T = TypeVar("T")


def unwrap(value: Union[T, Callable[[], T]]) -> T:
    if isinstance(value, Callable):
        return value()
    return value


def reflect_module_code(module: ModuleType) -> str:
    with open(module.__file__) as f:
        return f.read()
