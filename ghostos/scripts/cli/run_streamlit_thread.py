from ghostos.scripts.cli.utils import (
    start_streamlit_prototype_cli,
)
from ghostos.bootstrap import get_bootstrap_config
from pydantic import BaseModel, Field

__all__ = [
    "start_ghostos_thread_info",
    "ShowThreadInfo",
]


class ShowThreadInfo(BaseModel):
    thread_id: str = Field(description="thread id")


def start_ghostos_thread_info(thread_id: str):
    # path
    conf = get_bootstrap_config(local=True)
    workspace_dir = conf.abs_workspace_dir()
    args = ShowThreadInfo(thread_id=thread_id)
    start_streamlit_prototype_cli("run_thread_info.py", args.model_dump_json(), workspace_dir)
