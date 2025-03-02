from ghostos_common.helpers import create_and_bind_module
from ghostos.scripts.cli.run_aifunc import RunAIFuncApp
from ghostos.bootstrap import get_container
from ghostos.prototypes.streamlitapp.main import main_run
from ghostos.prototypes.streamlitapp.pages.router import default_router, AIFuncDetailRoute
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

    app_arg = RunAIFuncApp(**data)

    if app_arg.is_temp:
        # create temp module
        logger.debug(f"Create Temp module {app_arg.modulename}")
        create_and_bind_module(app_arg.modulename, app_arg.filename)

    # bootstrap container
    logger.debug(f"generate ghostos app container at workspace {app_arg.workspace_dir}")
    container = get_container()

    # bound route.
    page_route = AIFuncDetailRoute(aifunc_id=app_arg.import_path)
    # initialize router and set aifunc is default
    router = default_router().with_current(page_route)

    st.session_state["hello"] = "world"
    return [
        Singleton(container),
        Singleton(router),
    ]


main_run(bootstrap)
