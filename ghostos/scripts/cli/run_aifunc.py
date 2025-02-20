from sys import argv
from os import path
from typing import Optional, NamedTuple
from ghostos_common.helpers import import_from_path
from ghostos.scripts.cli.utils import check_ghostos_workspace_exists
from ghostos.prototypes.streamlitapp import cli
from ghostos.core.aifunc import AIFunc
from pydantic import BaseModel, Field
from ghostos_common.helpers import create_module, generate_import_path
from streamlit.web.cli import main_run

import inspect
import sys


class RunAIFuncApp(BaseModel):
    modulename: str = Field(description="expect aifunc modulename")
    filename: str = Field(description="expect aifunc filename")
    import_path: str = Field(description="expect aifunc import path")
    is_temp: bool = Field(description="if the modulename is temp module")
    workspace_dir: str = Field(description="the ghostos dir")


class FoundAIFunc(NamedTuple):
    aifunc: Optional[AIFunc]
    filename: str
    modulename: str
    is_temp: bool


def find_aifunc_by_name(filename_or_modulename: str) -> FoundAIFunc:
    if filename_or_modulename.endswith(".py"):
        filename = path.abspath(filename_or_modulename)
        module = create_module("ghostos_app.temp.aifunc", filename)
        is_temp = True
    else:
        module = import_from_path(filename_or_modulename)
        filename = module.__file__
        is_temp = False

    aifunc = None
    for name, value in module.__dict__.conversation_item_states():
        if name.startswith("_"):
            continue
        if not inspect.isclass(value):
            continue
        if value.__module__ != module.__name__:
            continue
        if issubclass(value, AIFunc):
            aifunc = value
            break
    return FoundAIFunc(aifunc, filename, module.__name__, is_temp)


def main():
    # path
    workspace_dir = check_ghostos_workspace_exists()

    # argument check
    args = argv[1:]
    if len(args) <= 0:
        raise ValueError("At least one argument (python filename or modulename) is required")
    filename_or_modulename = args[0]
    found = find_aifunc_by_name(filename_or_modulename)
    if found.aifunc is None:
        raise ValueError(f"No aifunc in module named {filename_or_modulename}")

    run_aifunc_app_arg = RunAIFuncApp(
        modulename=found.modulename,
        filename=found.filename,
        import_path=generate_import_path(found.aifunc),
        is_temp=found.is_temp,
        workspace_dir=workspace_dir,
    )
    script_path = path.join(path.dirname(cli.__file__), "run_aifunc_app.py")
    args = [script_path, run_aifunc_app_arg.model_dump_json(), *sys.argv[1:]]
    main_run(args)
