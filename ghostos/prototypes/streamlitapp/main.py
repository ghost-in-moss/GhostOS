from ghostos.bootstrap import application_container
from ghostos.prototypes.streamlitapp.app import run_ghostos_streamlit_app, SINGLETONS
from ghostos.prototypes.streamlitapp.utils.session import Singleton


def bootstrap() -> SINGLETONS:
    yield Singleton(application_container)


run_ghostos_streamlit_app(bootstrap)
