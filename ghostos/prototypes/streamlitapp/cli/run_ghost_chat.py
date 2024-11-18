from ghostos.helpers import create_and_bind_module
from ghostos.scripts.cli.run_streamlit_ghost import RunGhostChatApp
from ghostos.bootstrap import make_app_container, get_ghostos
from ghostos.prototypes.streamlitapp.main import main_run
from ghostos.prototypes.streamlitapp.pages.router import default_router, GhostChatPage
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.contracts.logger import get_console_logger
import streamlit as st
import sys
import json

if len(sys.argv) < 2:
    raise SystemExit(f"invalid RunAIFuncApp arguments")


def bootstrap():
    logger = get_console_logger()
    run_aifunc_app_arg = sys.argv[1]
    data = json.loads(run_aifunc_app_arg)

    app_arg = RunGhostChatApp(**data)

    if app_arg.is_temp:
        # create temp module
        logger.debug(f"Create Temp module {app_arg.modulename}")
        create_and_bind_module(app_arg.modulename, app_arg.filename)

    # bootstrap container
    logger.debug(f"generate ghostos app container at workspace {app_arg.workspace_dir}")
    container = make_app_container(app_arg.workspace_dir)

    # bound route.
    page_route = GhostChatPage(ghost_meta=app_arg.ghost_meta)
    # initialize router and set aifunc is default
    router = default_router().with_current(page_route)

    ghostos = get_ghostos(container)
    shell = ghostos.create_shell("ghostos_streamlit_app", "ghostos_streamlit_app")

    return [
        Singleton(container),
        Singleton(router),
        Singleton(ghostos),
        Singleton(shell),
    ]


main_run(bootstrap)
