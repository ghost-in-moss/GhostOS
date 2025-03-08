from __future__ import annotations
import sys
from typing import Tuple, List, NamedTuple, Any, Optional, Dict
from typing_extensions import Self
from types import ModuleType

from ghostos.bootstrap import expect_workspace_dir
from ghostos.contracts.logger import get_console_logger
from ghostos_common.helpers import create_module, import_from_path
from ghostos.abcd import Ghost
from pydantic import BaseModel, Field
from ghostos_common.entity import EntityMeta, to_entity_meta
from ghostos.ghosts.moss_ghost import new_moss_ghost
from streamlit.web.cli import main_run as run_streamlit_web
from os import path
import inspect
import json

__all__ = [
    'get_ghost_by_cli_argv',
    'get_or_create_module_from_name',
    'find_ghost_by_file_or_module',
    'check_ghostos_workspace_exists',
    'parse_args_modulename_or_filename',
    'DirGhostsConf', 'GhostInfo',
    'get_streamlit_config_flag_options',
    'start_streamlit_prototype_cli',
]


def get_streamlit_config_flag_options(workspace_dir: str) -> List[str]:
    from toml import loads
    filename = path.join(workspace_dir, ".streamlit/config.toml")
    with open(filename, "r") as f:
        data = loads(f.read())
    flags = []
    for key in data:
        attrs = data[key]
        for attr_name in attrs:
            value = attrs[attr_name]
            flags.append(f"--{key}.{attr_name}={value}")
    return flags


def get_ghost_by_cli_argv() -> Tuple[GhostInfo, ModuleType, str, bool]:
    filename_or_modulename, args = parse_args_modulename_or_filename()
    return find_ghost_by_file_or_module(filename_or_modulename)


def find_ghost_by_file_or_module(filename_or_modulename: str) -> Tuple[GhostInfo, ModuleType, str, bool]:
    """
    :param filename_or_modulename:
    :return: (ghost_info, found_module, found_file, file_is_temp)
    """
    found = get_or_create_module_from_name(filename_or_modulename, "ghostos.temp.ghost")
    # ghost info
    ghosts_conf = DirGhostsConf.load_from(filename_or_modulename)
    ghost_key = DirGhostsConf.file_ghost_key(filename_or_modulename)
    if ghost_key in ghosts_conf.ghosts:
        ghost_info = ghosts_conf.ghosts[ghost_key]
        return ghost_info, found.module, found.filename, found.is_temp

    if found.value is not None:
        if not isinstance(found.value, Ghost):
            raise SystemExit(f"{found.value} is not a Ghost object")
        ghost = found.value
    elif "__ghost__" in found.module.__dict__:
        ghost = found.module.__dict__["__ghost__"]
        if not isinstance(ghost, Ghost):
            raise SystemExit(f"{filename_or_modulename} __ghost__ is not a Ghost object")
    else:
        ghost = new_moss_ghost(
            found.module.__name__,
        )

    ghost_info = GhostInfo(
        ghost=to_entity_meta(ghost),
    )
    return ghost_info, found.module, found.filename, found.is_temp


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
    from os import path, getcwd

    _, extension = path.splitext(filename_or_modulename)
    if extension in ACCEPTED_FILE_EXTENSIONS:
        filename = path.abspath(filename_or_modulename)
        root_dir = getcwd()
        if filename.startswith(root_dir):
            relative_path = filename[len(root_dir) + 1:]
            relative_path_basename, _ = path.splitext(relative_path)
            temp_modulename = relative_path_basename.replace("/", ".")
            if temp_modulename.endswith(".__init__"):
                temp_modulename = temp_modulename[:-len(".__init__")]
        if temp_modulename in sys.modules:
            module = sys.modules[temp_modulename]
        else:
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


class GhostInfo(BaseModel):
    ghost: EntityMeta = Field(description="ghost meta")
    context: Optional[EntityMeta] = Field(None)


class DirGhostsConf(BaseModel):
    ghosts: Dict[str, GhostInfo] = Field(
        default_factory=dict,
        description="ghost info dict, from filename to ghost info",
    )

    @classmethod
    def load(cls, filename: str) -> Self:
        from os.path import exists
        if exists(filename):
            with open(filename, "r") as f:
                content = f.read()
                data = json.loads(content)
                return cls(**data)
        return cls()

    @classmethod
    def load_from(cls, filename: str) -> Self:
        ghosts_filename = cls.ghosts_filename(filename)
        return cls.load(ghosts_filename)

    @classmethod
    def file_ghost_key(cls, filename: str) -> str:
        from os.path import basename, splitext
        file_basename = basename(filename)
        key, _ = splitext(file_basename)
        return key

    @classmethod
    def ghosts_filename(cls, filename: str) -> str:
        from os.path import dirname, join
        dir_ = dirname(filename)
        ghosts_filename = join(dir_, ".ghosts.yml")
        return ghosts_filename

    def save(self, filename: str) -> None:
        ghosts_filename = self.ghosts_filename(filename)
        content = self.model_dump_json(indent=2)
        with open(ghosts_filename, "w") as f:
            f.write(content)


def start_streamlit_prototype_cli(filename: str, cli_args: str, workspace_dir: str):
    from ghostos.prototypes.streamlitapp import cli
    script_path = path.join(path.dirname(cli.__file__), filename)
    args = [script_path, cli_args]

    flags = get_streamlit_config_flag_options(workspace_dir)
    args.extend(flags)
    run_streamlit_web(args)
