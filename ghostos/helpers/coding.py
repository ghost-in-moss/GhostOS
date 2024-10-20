from types import ModuleType
import inspect


def reflect_module_code(module: ModuleType) -> str:
    with open(module.__file__) as f:
        return f.read()
