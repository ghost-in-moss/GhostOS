import inspect
from typing import Any, Tuple, Optional, Dict, Callable, Type, TypeVar
from types import ModuleType
import os
import sys

__all__ = [
    'Importer',
    'import_from_path',
    'import_class_from_path',
    'import_instance_from_path',
    'get_calling_modulename',
    'get_module_attr',
    'generate_import_path',
    'generate_module_and_attr_name',
    'join_import_module_and_spec',
    'is_method_belongs_to_class',
    'parse_import_path_module_and_attr_name',
    'rewrite_module',
    'rewrite_module_by_path',
    'create_module',
    'create_and_bind_module',
    'get_module_fullname_from_path',
]

Importer = Callable[[str], ModuleType]

T = TypeVar('T', bound=type)
I = TypeVar('I')


def import_class_from_path(path: str, parent: Optional[T]) -> T:
    imported = import_from_path(path)
    if parent and inspect.isclass(imported) and not issubclass(imported, parent):
        raise TypeError(f'{path} is not a subclass of {parent}')
    return imported


def import_instance_from_path(path: str, parent: Optional[Type[I]]) -> I:
    imported = import_from_path(path)
    if parent and inspect.isclass(imported) and not isinstance(imported, parent):
        raise TypeError(f'{path} is not a instance of {parent}')
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
        return get_module_attr(imported_module.__dict__, spec)
    return imported_module


def get_module_attr(module, attr_name: str) -> Optional[Any]:
    parts = attr_name.split('.')
    value = module
    for part in parts:
        if value is None:
            raise AttributeError(f'Module has no attribute {attr_name}')
        if part == "<locals>":
            raise AttributeError(f'local attribute {attr_name} is not support yet')
        if isinstance(value, Dict):
            value = value.get(part)
        else:
            value = getattr(value, part)
    return value


def generate_module_and_attr_name(value: Any) -> Tuple[str, Optional[str]]:
    if inspect.ismodule(value):
        return value.__name__, None
    elif inspect.isclass(value) or inspect.isfunction(value) or hasattr(value, "__module__"):
        modulename = getattr(value, '__module__', '')
        if modulename.endswith(".__init__"):
            modulename = modulename[:-len(".__init__")]
        attr_name = getattr(value, '__qualname__', getattr(value, '__name__', ""))
        return modulename, attr_name
    else:
        raise AttributeError(f'value {value} should be module or class to generate module spec')


def parse_import_path_module_and_attr_name(import_path: str) -> Tuple[str, Optional[str]]:
    """
    parse import_path to modulename and spec
    :param import_path: pattern is `module:spec`
    :return: modulename, spec
    """
    parts = import_path.split(':', 2)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def create_module(module_name: str, file_path: str):
    from importlib import util

    # 加载模块
    spec = util.spec_from_file_location(module_name, file_path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def get_module_fullname_from_path(file_path: str, use_longest_match: bool = True) -> Optional[str]:
    """
    根据文件的绝对路径反解出模块名。

    Args:
        file_path (str): 文件的绝对路径。
        use_longest_match (bool): 是否优先使用最长匹配路径。默认为 True。

    Returns:
        Optional[str]: 模块名，如果无法反解则返回 None。
    """
    # 获取文件的绝对路径
    abs_path = os.path.abspath(file_path)

    # 获取模块名（去掉 .py 后缀）
    module_name = inspect.getmodulename(abs_path)
    if not module_name:
        return None

    # 如果文件是 __init__.py，模块名应该是其所在目录的名称
    if module_name == "__init__":
        module_name = os.path.basename(os.path.dirname(abs_path))
        abs_path = os.path.dirname(abs_path)

    # 找到 sys.path 中匹配的前缀路径
    matches = []
    for path in sys.path:
        if not path:
            continue  # 跳过空路径
        path = os.path.abspath(path)  # 确保路径是绝对路径
        if abs_path.startswith(path):
            matches.append(path)

    if not matches:
        # 如果没有匹配的路径，直接返回模块名
        return module_name

    # 根据 use_longest_match 选择最长或最短匹配路径
    if use_longest_match:
        best_match = max(matches, key=len)  # 最长路径
    else:
        best_match = min(matches, key=len)  # 最短路径

    # 获取文件路径相对于最佳匹配路径的相对路径
    relative_path = os.path.relpath(abs_path, best_match)

    # 将路径中的目录分隔符替换为点，并去掉 .py 后缀
    module_path = os.path.splitext(relative_path)[0]
    module_path = module_path.replace(os.sep, ".")

    return module_path


def create_and_bind_module(modulename: str, filename: str, force: bool = False):
    from sys import modules
    if not force and modulename in modules:
        return modules[modulename]
    module = create_module(modulename, filename)
    modules[modulename] = module
    return module


def generate_import_path(value: Any) -> str:
    module, spec = generate_module_and_attr_name(value)
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
