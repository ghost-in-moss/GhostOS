from typing import Iterable
from ghostos.prototypes.streamlitapp.pages.router import AIFuncListRoute, AIFuncDetailRoute
from ghostos.prototypes.streamlitapp.resources import (
    get_container,
    get_app_conf,
    get_app_docs,
)
from ghostos.prototypes.streamlitapp.widgets.dialogs import (
    open_code_dialog
)
from ghostos.core.aifunc import (
    AIFuncRepository
)
import ghostos.core.aifunc.func as func
import ghostos.core.aifunc.interfaces as interfaces
from ghostos_common.identifier import Identifier
from ghostos_common.helpers import (
    gettext as _,
    reflect_module_code,
)
import streamlit as st


def render_aifuncs(items: Iterable[Identifier], keyword: str = "") -> None:
    for idt in items:
        if not idt.match_keyword(keyword):
            continue
        with st.container(border=True):
            st.subheader(idt.name)
            st.caption(idt.id)
            st.markdown(idt.description)
            key = idt.id + ":run"
            if st.button("run", key=key):
                route = AIFuncDetailRoute(
                    aifunc_id=idt.id,
                )
                route.switch_page()


def main():
    # bind if route value not bind before
    route = AIFuncListRoute().get_or_bind(st.session_state)
    app_conf = get_app_conf()
    # render title and description.
    st.title(_("AI Functions"))
    with st.expander(_("introduce"), expanded=app_conf.BoolOpts.HELP_MODE.get()):
        doc = get_app_docs().read("aifunc/introduction")
        st.markdown(doc)

        code_pattern = "AIFunc Code Pattern"
        contracts_pattern = "AIFunc Interfaces"

        if st.button(code_pattern):
            file_code = reflect_module_code(func)
            open_code_dialog(code_pattern, file_code)
        if st.button(contracts_pattern):
            file_code = reflect_module_code(interfaces)
            open_code_dialog(contracts_pattern, file_code)

    # scan
    repo = get_container().force_fetch(AIFuncRepository)
    with st.expander(_("tools"), expanded=app_conf.BoolOpts.DEBUG_MODE.get()):
        do_scan = st.text_input(
            label=_("scan ai funcs"),
            value="",
            placeholder=_("input python module name, scan all the funcs recursively"),
        )

    if do_scan:
        found = repo.scan(do_scan, recursive=True, save=True)
        st.write(f"Found {len(found)} AIFuncs")
        render_aifuncs(found)
    else:
        funcs = list(repo.list())
        col1, col2 = st.columns([2, 1])
        with col2:
            keyword = st.text_input(
                label=_("filter by keyword"),
                help=_("filter the funcs list by keyword"),
                value=route.search,
            )
        render_aifuncs(funcs, keyword)
