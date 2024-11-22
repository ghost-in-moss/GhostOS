from typing import Optional, Dict, List
from ghostos.scripts.cli.utils import (
    check_ghostos_workspace_exists,
    get_ghost_by_cli_argv,
)
from streamlit.web.cli import main_run
from ghostos.prototypes.streamlitapp import cli
from ghostos.entity import EntityMeta
from ghostos.core.moss.utils import escape_string_quotes
from pydantic import BaseModel, Field
import sys
from os import path


class RunGhostChatApp(BaseModel):
    modulename: str = Field(description="expect ghost modulename")
    filename: str = Field(description="expect ghost filename")
    is_temp: bool = Field(description="if the modulename is temp module")
    workspace_dir: str = Field(description="the ghostos dir")
    ghost_meta: EntityMeta
    context_meta: Optional[EntityMeta] = Field(default=None)


def get_config_flag_options(workspace_dir: str) -> List[str]:
    from os.path import join, dirname
    from toml import loads
    filename = join(workspace_dir, ".streamlit/config.toml")
    with open(filename, "r") as f:
        data = loads(f.read())
    flags = []
    for key in data:
        attrs = data[key]
        for attr_name in attrs:
            value = attrs[attr_name]
            flags.append(f"{key}.{attr_name}=`{value}`")
    return flags


def main():
    # path
    workspace_dir = check_ghostos_workspace_exists()
    ghost_info, modulename, filename, is_temp = get_ghost_by_cli_argv()
    args = RunGhostChatApp(
        modulename=modulename,
        filename=filename,
        is_temp=is_temp,
        workspace_dir=workspace_dir,
        ghost_meta=ghost_info.ghost,
        context_meta=ghost_info.context,
    )
    script_path = path.join(path.dirname(cli.__file__), "run_ghost_chat.py")
    args = [script_path, args.model_dump_json(), *sys.argv[1:]]

    flags = get_config_flag_options(workspace_dir)
    args.extend(flags)
    main_run(args)
