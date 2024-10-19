import inspect
from typing import Any, Tuple, Optional, Dict, Callable, Type, TypeVar
from types import ModuleType

__all__ = [
    'Importer',
    'import_from_path',
    'import_class_from_path',
    'get_calling_modulename',
    'get_module_spec',
    'generate_import_path',
    'generate_module_spec',
    'join_import_module_and_spec',
    'is_method_belongs_to_class',
    'parse_import_module_and_spec',
    'rewrite_module',
    'rewrite_module_by_path',
]

Importer = Callable[[str], ModuleType]

T = TypeVar('T', bound=type)


def import_class_from_path(path: str, parent: Optional[T]) -> T:
    imported = import_from_path(path)
    if parent and not issubclass(imported, parent):
        raise TypeError(f'{path} is not a subclass of {parent}')
    return imported


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
            raise AttributeError(f'local attribute {spec} is not support yet')
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


def is_method_belongs_to_class(method: Callable, cls: Type) -> bool:
    method_module = getattr(method, '__module__', None)
    cls_module = getattr(cls, '__module__', None)
    if method_module is None or cls_module is None or method_module != cls_module:
        return False
    method_qualname = getattr(method, '__qualname__', "")
    cls_qualname = getattr(cls, '__qualname__', "")
    return method_qualname != cls_qualname and method_qualname.startswith(cls_qualname)


def get_calling_modulename(skip: int = 0) -> Optional[str]:
    stack = inspect.stack()
    start = 0 + skip + 1
    if len(stack) < start + 1:
        return None
    frame = stack[start][0]

    # module and packagename.
    module_info = inspect.getmodule(frame)
    if module_info:
        mod = module_info.__name__
        return mod
    return None


def rewrite_module_by_path(module_path: str, code: str) -> None:
    """
    rewrite a module from module_path with code
    :param module_path:
    :param code:
    """
    module = import_from_path(module_path)
    rewrite_module(module, code)


def rewrite_module(module: ModuleType, code: str) -> None:
    """
    write code to target module
    :param module:
    :param code:
    """
    filename = inspect.getfile(module)
    with open(filename, 'w') as f:
        f.write(code)
