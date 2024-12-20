from typing import List

from ghostos.core.messages import Message
from ghostos.core.runtime import Event
from ghostos.contracts.logger import get_ghostos_logger
from ghostos.helpers import create_and_bind_module
from ghostos.scripts.cli.run_streamlit_app import RunGhostChatApp
from ghostos.bootstrap import get_ghostos, get_container
from ghostos.prototypes.streamlitapp.main import main_run
from ghostos.prototypes.streamlitapp.pages.router import default_router, GhostChatRoute
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.abcd import Shell, Background
from ghostos.abcd.utils import get_module_magic_shell_providers
import importlib
import streamlit as st
import sys
import json

if len(sys.argv) < 2:
    raise SystemExit(f"invalid RunAIFuncApp arguments")

logger = get_ghostos_logger()


class StreamlitBackgroundApp(Background):

    def on_error(self, error: Exception) -> bool:
        logger.exception(error)
        return True

    def on_event(self, event: Event, messages: List[Message]) -> None:
        pass

    def alive(self) -> bool:
        from streamlit.runtime import Runtime, RuntimeState
        state = Runtime.instance().state
        # if streamlit is closed, close ghostos shell
        return state not in {RuntimeState.STOPPING, RuntimeState.STOPPED}

    def halt(self) -> int:
        return 0


def bootstrap():
    run_aifunc_app_arg = sys.argv[1]
    data = json.loads(run_aifunc_app_arg)

    app_arg = RunGhostChatApp(**data)

    if app_arg.is_temp:
        # create temp module
        logger.debug(f"Create Temp module {app_arg.modulename}")
        started_module = create_and_bind_module(app_arg.modulename, app_arg.filename)
    else:
        started_module = importlib.import_module(app_arg.modulename)

    providers = get_module_magic_shell_providers(started_module)

    # bootstrap container
    logger.debug(f"generate ghostos app container at workspace {app_arg.workspace_dir}")

    # bound route.
    page_route = GhostChatRoute(
        ghost_meta=app_arg.ghost_meta,
        context_meta=app_arg.context_meta,
        filename=app_arg.filename,
    )
    page_route = page_route.get_or_bind(st.session_state)
    # initialize router and set aifunc is default
    router = default_router().with_current(page_route)

    ghostos = get_ghostos()
    shell = Singleton.get(Shell, st.session_state, force=False)
    container = get_container()
    if shell is None:
        logger.debug("start shell background run")
        shell = ghostos.create_shell(
            "ghostos_streamlit_app",
            providers=providers,
        )
        shell.background_run(4, StreamlitBackgroundApp())
        Singleton(shell, Shell).bind(st.session_state)

    return [
        Singleton(container),
        Singleton(router),
    ]


try:
    main_run(bootstrap)
except RuntimeError as e:
    SystemExit(e)
