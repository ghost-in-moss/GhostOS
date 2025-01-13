from typing import Optional, List
from ghostos.scripts.cli.utils import (
    GhostInfo,
)
from streamlit.web.cli import main_run as run_streamlit_web
from ghostos.prototypes.streamlitapp import cli
from ghostos.bootstrap import get_bootstrap_config
from ghostos.entity import EntityMeta
from pydantic import BaseModel, Field
from os import path

__all__ = [
    "start_streamlit_prototype_cli",
    "RunGhostChatApp",
    "get_config_flag_options",
    "start_ghost_app",
]


class RunGhostChatApp(BaseModel):
    modulename: str = Field(description="expect ghost modulename")
    filename: str = Field(description="expect ghost filename")
    is_temp: bool = Field(description="if the modulename is temp module")
    workspace_dir: str = Field(description="the ghostos dir")
    ghost_meta: EntityMeta
    context_meta: Optional[EntityMeta] = Field(default=None)


def get_config_flag_options(workspace_dir: str) -> List[str]:
    from os.path import join
    from toml import loads
    filename = join(workspace_dir, ".streamlit/config.toml")
    with open(filename, "r") as f:
        data = loads(f.read())
    flags = []
    for key in data:
        attrs = data[key]
        for attr_name in attrs:
            value = attrs[attr_name]
            flags.append(f"--{key}.{attr_name}={value}")
    return flags


def start_ghost_app(ghost_info: GhostInfo, modulename: str, filename: str, is_temp: bool):
    # path
    conf = get_bootstrap_config(local=True)
    workspace_dir = conf.abs_workspace_dir()
    args = RunGhostChatApp(
        modulename=modulename,
        filename=filename,
        is_temp=is_temp,
        workspace_dir=workspace_dir,
        ghost_meta=ghost_info.ghost,
        context_meta=ghost_info.context,
    )
    start_streamlit_prototype_cli("run_ghost_chat.py", args.model_dump_json(), workspace_dir)


def start_streamlit_prototype_cli(filename: str, cli_args: str, workspace_dir: str):
    script_path = path.join(path.dirname(cli.__file__), filename)
    args = [script_path, cli_args]

    flags = get_config_flag_options(workspace_dir)
    args.extend(flags)
    run_streamlit_web(args)
