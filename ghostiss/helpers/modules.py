from typing import Any, Tuple, Optional


def import_from_str(module_spec: str) -> Any:
    from importlib import import_module
    parts = module_spec.split(':', 2)
    module = parts[0]
    spec = parts[1] if len(parts) > 1 else None
    imported_module = import_module(module)
    if spec:
        if spec in imported_module:
            return getattr(imported_module, spec)
        raise ModuleNotFoundError(f"No spec named {spec} in module {module}")
    return imported_module


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
