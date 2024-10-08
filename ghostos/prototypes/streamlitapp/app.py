import streamlit as st
from typing import Callable, List
from ghostos.container import Container
from ghostos.prototypes.streamlitapp.utils.session import expect, SingletonContracts, Singleton
from ghostos.prototypes.streamlitapp.pages.navigation import navigation

__all__ = [
    "SINGLETONS", "BOOTSTRAP", "BOOTSTRAPPED_KEY",
    "contracts", "validate_container",
    "run_ghostos_streamlit_app",
]

SINGLETONS = List[Singleton]

BOOTSTRAP = Callable[[], SINGLETONS]

BOOTSTRAPPED_KEY = "ghostos.streamlit.app.bootstrapped"

contracts = SingletonContracts([
    Container,
])


def validate_container(container: Container) -> None:
    pass


def boot(fn: BOOTSTRAP) -> None:
    if not expect(st.session_state, BOOTSTRAPPED_KEY, True):
        singletons = fn()
        for s in singletons:
            s.bind(st.session_state, force=False)
        unbound = contracts.validate(st.session_state)
        if unbound:
            error = ",".join([str(c) for c in unbound])
            raise NotImplementedError(f'GhostOS Streamlit app unbound contracts: {error}')
        # validate the container bootstrapped outside.
        container = Singleton.get(Container, st.session_state)
        validate_container(container)
        st.session_state[BOOTSTRAPPED_KEY] = True


def run_ghostos_streamlit_app(bootstrap: BOOTSTRAP) -> None:
    """
    run streamlit application with outside bootstrap function.
    :param bootstrap: a bootstrap function defined outside the streamlit app run

    Why we need bootstrap argument when there is streamlit.cache_resource?
    1. I need a streamlit app func which can run everywhere
    2. The ghostos streamlit app need some contracts (for example, workspace), bootstrapped outside cause 1.
    3. @st.cache_resource wrap a function who control the resources lifecycle, conflict to 2.
    """
    # bootstrap once
    boot(bootstrap)
    # load pages
    pgs = st.navigation(navigation.pages(), position="hidden")
    # define sidebar
    with st.sidebar:
        navigation.render_sidebar_page_links()

    pgs.run()
