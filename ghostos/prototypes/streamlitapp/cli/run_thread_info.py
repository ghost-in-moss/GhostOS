from ghostos.contracts.logger import get_ghostos_logger
from ghostos.scripts.cli.run_streamlit_thread import ShowThreadInfo
from ghostos.bootstrap import get_container
from ghostos.prototypes.streamlitapp.main import main_run
from ghostos.prototypes.streamlitapp.pages.router import default_router, ShowThreadRoute
from ghostos.prototypes.streamlitapp.utils.session import Singleton
import streamlit as st
import sys
import json

if len(sys.argv) < 2:
    raise SystemExit(f"invalid RunAIFuncApp arguments")

logger = get_ghostos_logger()


def bootstrap():
    run_aifunc_app_arg = sys.argv[1]
    data = json.loads(run_aifunc_app_arg)

    args = ShowThreadInfo(**data)

    # bound route.
    page_route = ShowThreadRoute(
        thread_id=args.thread_id,
    )
    page_route = page_route.get_or_bind(st.session_state)
    # initialize router and set aifunc is default
    router = default_router().with_current(page_route)
    container = get_container()

    return [
        Singleton(container),
        Singleton(router),
    ]


try:
    main_run(bootstrap)
except RuntimeError as e:
    SystemExit(e)
