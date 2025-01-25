from typing import Optional
from ghostos.scripts.cli.utils import (
    GhostInfo, start_streamlit_prototype_cli,
)
from ghostos.bootstrap import get_bootstrap_config
from ghostos.entity import EntityMeta
from pydantic import BaseModel, Field

__all__ = [
    "RunGhostChatApp",
    "start_ghost_app",
]


class RunGhostChatApp(BaseModel):
    modulename: str = Field(description="expect ghost modulename")
    filename: str = Field(description="expect ghost filename")
    is_temp: bool = Field(description="if the modulename is temp module")
    workspace_dir: str = Field(description="the ghostos dir")
    ghost_meta: EntityMeta
    context_meta: Optional[EntityMeta] = Field(default=None)


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
