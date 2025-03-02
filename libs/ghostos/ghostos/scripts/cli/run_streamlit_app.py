from typing import Optional
from ghostos.scripts.cli.utils import (
    GhostInfo, start_streamlit_prototype_cli,
)
from ghostos.abcd import Ghost, Context
from ghostos.bootstrap import get_bootstrap_config
from ghostos_common.entity import EntityMeta, to_entity_meta
from pydantic import BaseModel, Field

__all__ = [
    "RunGhostChatApp",
    "start_streamlit_app_by_ghost_info",
    'start_streamlit_app_by_ghost',
]


class RunGhostChatApp(BaseModel):
    modulename: str = Field(description="expect ghost modulename")
    filename: str = Field(description="expect ghost filename")
    is_temp: bool = Field(description="if the modulename is temp module")
    workspace_dir: str = Field(description="the ghostos dir")
    ghost_meta: EntityMeta
    context_meta: Optional[EntityMeta] = Field(default=None)


def start_streamlit_app_by_ghost(
        ghost: Ghost,
        context: Optional[Context] = None,
        modulename: str = "",
        filename: str = "",
):
    ghost_info = GhostInfo(
        ghost=to_entity_meta(ghost),
        context=to_entity_meta(context) if context else None,
    )
    start_streamlit_app_by_ghost_info(ghost_info, modulename, filename, is_temp=False)


def start_streamlit_app_by_ghost_info(ghost_info: GhostInfo, modulename: str, filename: str, is_temp: bool):
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
