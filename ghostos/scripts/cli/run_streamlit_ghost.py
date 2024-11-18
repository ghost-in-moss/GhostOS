from ghostos.scripts.cli.utils import (
    check_ghostos_workspace_exists,
    get_ghost_by_cli_argv,
)
from streamlit.web.cli import main_run
from ghostos.prototypes.streamlitapp import cli
from ghostos.entity import EntityMeta, to_entity_meta
from pydantic import BaseModel, Field
import sys
from os import path


class RunGhostChatApp(BaseModel):
    modulename: str = Field(description="expect ghost modulename")
    filename: str = Field(description="expect ghost filename")
    is_temp: bool = Field(description="if the modulename is temp module")
    workspace_dir: str = Field(description="the ghostos dir")
    ghost_meta: EntityMeta


def main():
    # path
    workspace_dir = check_ghostos_workspace_exists()
    ghost, modulename, filename, is_temp = get_ghost_by_cli_argv()
    args = RunGhostChatApp(
        modulename=modulename,
        filename=filename,
        is_temp=is_temp,
        workspace_dir=workspace_dir,
        ghost_meta=to_entity_meta(ghost),
    )
    script_path = path.join(path.dirname(cli.__file__), "run_ghost_chat.py")
    args = [script_path, args.model_dump_json(), *sys.argv[1:]]
    main_run(args)
