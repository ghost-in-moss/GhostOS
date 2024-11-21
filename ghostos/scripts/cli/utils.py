import sys
from typing import Tuple, List, NamedTuple, Any, Optional
from types import ModuleType

from ghostos.bootstrap import expect_workspace_dir
from ghostos.contracts.logger import get_console_logger
from ghostos.helpers import create_module, import_from_path
import inspect
from ghostos.abcd import Ghost

__all__ = [
    'get_ghost_by_cli_argv',
    'get_or_create_module_from_name',
    'check_ghostos_workspace_exists',
    'parse_args_modulename_or_filename',
]


def get_ghost_by_cli_argv() -> Tuple[Ghost, str, str, bool]:
    filename_or_modulename, args = parse_args_modulename_or_filename()
    found = get_or_create_module_from_name(filename_or_modulename, "ghostos.temp.agent")

    if found.value is not None:
        if not isinstance(found.value, Ghost):
            raise SystemExit(f"{found.value} is not a Ghost object")
        ghost = found.value
    elif "__ghost__" in found.module.__dict__:
        ghost = found.module.__dict__["__ghost__"]
        if not isinstance(ghost, Ghost):
            raise SystemExit(f"{filename_or_modulename} __ghost__ is not a Ghost object")
    else:
        raise SystemExit(f"cant find ghost instance at {filename_or_modulename}")
    return ghost, found.module.__name__, found.filename, found.is_temp


def check_ghostos_workspace_exists() -> str:
    logger = get_console_logger()
    app_dir, ok = expect_workspace_dir()
    if not ok:
        logger.error("expect GhostOS workspace `%s` is not found. ", app_dir)
        logger.debug("run `ghostos init` to create workspace")
        sys.exit(0)
    return app_dir


def parse_args_modulename_or_filename() -> Tuple[str, List[str]]:
    from sys import argv
    # argument check
    args = argv[1:]
    if len(args) <= 0:
        raise ValueError("At least one argument (python filename or modulename) is required")
    filename_or_modulename = args[0]
    return filename_or_modulename, args


class Found(NamedTuple):
    value: Optional[Any]
    module: ModuleType
    filename: str
    is_temp: bool


ACCEPTED_FILE_EXTENSIONS = (".py", ".py3")


def get_or_create_module_from_name(
        filename_or_modulename: str,
        temp_modulename: str,
) -> Found:
    from os import path
    _, extension = path.splitext(filename_or_modulename)
    if extension in ACCEPTED_FILE_EXTENSIONS:
        filename = path.abspath(filename_or_modulename)
        module = create_module(temp_modulename, filename)
        is_temp = True
        value = None
    else:
        imported = import_from_path(filename_or_modulename)
        if isinstance(imported, ModuleType):
            module = imported
            value = None
        else:
            module = inspect.getmodule(imported)
            value = imported
        filename = module.__file__
        is_temp = False
    return Found(value, module, filename, is_temp)
