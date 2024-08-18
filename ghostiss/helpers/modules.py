import inspect
from typing import Any, Tuple, Optional, Dict, Callable
from types import ModuleType

Importer = Callable[[str], ModuleType]


def import_from_path(module_spec: str, importer: Optional[Importer] = None) -> Any:
    if importer is None:
        from importlib import import_module
        importer = import_module
    parts = module_spec.split(':', 2)
    module = parts[0]
    spec = parts[1] if len(parts) > 1 else None
    imported_module = importer(module)
    if spec:
        return get_module_spec(imported_module.__dict__, spec)
    return imported_module


def get_module_spec(module, spec: str) -> Optional[Any]:
    parts = spec.split('.')
    value = module
    for part in parts:
        if value is None:
            raise AttributeError(f'Module has no attribute {spec}')
        if part == "<locals>":
            raise AttributeError(f'local attribute {spec} is not allowed to get')
        if isinstance(value, Dict):
            value = value.get(part)
        else:
            value = getattr(value, part)
    return value


def generate_module_spec(value: Any) -> Tuple[str, Optional[str]]:
    if inspect.ismodule(value):
        return value.__name__, None
    elif inspect.isclass(value):
        module = getattr(value, '__module__', '')
        spec = getattr(value, '__qualname__', getattr(value, '__name__', ""))
        return module, spec
    else:
        raise AttributeError(f'value {value} should be module or class to generate module spec')


def parse_import_module_and_spec(import_path: str) -> Tuple[str, Optional[str]]:
    """
    parse import_path to modulename and spec
    :param import_path: pattern is `module:spec`
    :return: modulename, spec
    """
    parts = import_path.split(':', 2)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def generate_import_path(value: Any) -> str:
    module, spec = generate_module_spec(value)
    return join_import_module_and_spec(module, spec)


def join_import_module_and_spec(modulename: str, spec: Optional[str]) -> str:
    attr = ""
    if spec:
        attr = f":{spec}"
    return f"{modulename}{attr}"
