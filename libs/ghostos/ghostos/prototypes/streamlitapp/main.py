import streamlit as st
from typing import Callable, List
from ghostos_container import Container, Contracts
from ghostos.contracts.configs import Configs
from ghostos.prototypes.streamlitapp.utils.session import expect, SingletonContracts, Singleton
from ghostos.prototypes.streamlitapp.utils.route import Router
from ghostos.prototypes.streamlitapp.resources import AppConf
from ghostos_common.helpers import gettext as _

__all__ = [
    "SINGLETONS", "BOOTSTRAP", "BOOTSTRAPPED_KEY",
    "streamlit_contracts",
    "container_contracts",
    "SingletonContracts",
    "Singleton",
    "main_run",
]

st.set_page_config(page_title='GhostOS')

SINGLETONS = List[Singleton]

BOOTSTRAP = Callable[[], SINGLETONS]

BOOTSTRAPPED_KEY = "ghostos.streamlit.app.bootstrapped"

container_contracts = Contracts([
    Configs,
])

streamlit_contracts = SingletonContracts([
    Container,
    Router,
])


def boot(fn: BOOTSTRAP) -> None:
    if expect(st.session_state, BOOTSTRAPPED_KEY, True):
        return
    singletons = fn()
    for s in singletons:
        s.bind(st.session_state, force=False)

    # validate streamlit bounds
    unbound = streamlit_contracts.validate(st.session_state)
    if unbound:
        error = ",".join([str(c) for c in unbound])
        raise NotImplementedError(f'GhostOS Streamlit app unbound contracts: {error}')

    # validate container bounds
    container = Singleton.get(Container, st.session_state)
    container_contracts.validate(container)
    # validate the container bootstrapped outside.
    st.session_state[BOOTSTRAPPED_KEY] = True


def main_run(bootstrap: BOOTSTRAP) -> None:
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
    router = Singleton.get(Router, st.session_state)
    pgs = st.navigation(router.pages(), position="hidden")
    # define sidebar
    with st.sidebar:
        # router.render_homepage()
        # render page links
        with st.expander(label=_("Navigator"), expanded=False, icon=":material/menu:"):
            router.render_navigator(use_container_width=True)
        # with helper mode toggle
        # open_navigator = st.button(
        #     label=_("GhostOS Navigator"),
        #     help=_("the navigations"),
        #     icon=":material/menu:",
        #     use_container_width=True,
        # )
        with st.expander(label="Options", expanded=True, icon=":material/settings:"):
            AppConf.BoolOpts.HELP_MODE.render_toggle(
                label=_("Help Mode"),
                tips=_("switch help mode at every page"),
            )
            AppConf.BoolOpts.DEBUG_MODE.render_toggle(
                label=_("Debug Mode"),
                tips=_("switch debug mode at every page"),
            )
        st.subheader(_("Menu"))

    # global navigator dialog
    # if open_navigator:
    #     app_navigator_dialog()

    try:
        pgs.run()
    except Exception as e:
        st.exception(e)
