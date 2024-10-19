import inspect
from typing import List, Iterable
import streamlit as st
from ghostos.prototypes.streamlitapp.navigation import AIFuncListRoute, AIFuncDetailRoute
from ghostos.prototypes.streamlitapp.resources import (
    get_container,
    get_app_conf,
    get_app_docs,
)
from ghostos.prototypes.streamlitapp.widgets import open_code_dialog, help_document, markdown_document
from ghostos.core.aifunc import AIFuncRepository, AIFunc, get_aifunc_result_type
from ghostos.core.aifunc import func, interfaces
from ghostos.common import Identifier, identify_class
from ghostos.helpers import (
    gettext as _,
    reflect_module_code,
    import_from_path,
    import_class_from_path, generate_import_path,
    parse_import_module_and_spec,
)
import inspect
import webbrowser


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


def aifuncs_list():
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


def aifunc_detail():
    route = AIFuncDetailRoute().get_or_bind(st.session_state)
    with st.sidebar:
        AIFuncListRoute().render_page_link(use_container_width=True)

    if not route.aifunc_id:
        st.error("No AI Functions found")
        return
    try:
        fn = import_class_from_path(route.aifunc_id, AIFunc)
    except TypeError as e:
        st.error(e)
        return

    idt = identify_class(fn)

    # 渲染全局信息.
    st.title(idt.name)
    st.caption(idt.id)
    st.markdown(idt.description)

    tab_exec, tab_source = st.tabs([_("Execute AIFuncs"), _("Source Code")])
    with tab_exec:
        st.write("hello")

    with tab_source:
        # prepare
        module_name, attr_name = parse_import_module_and_spec(idt.id)
        mod = import_from_path(module_name)
        result_type = get_aifunc_result_type(fn)

        # open source code
        if st.button("Open The Source File"):
            webbrowser.open(f"file://{mod.__file__}")

        # func code panel
        st.subheader(_("Func Request"))
        st.caption(idt.id)
        source = inspect.getsource(fn)
        st.code(source, line_numbers=True, wrap_lines=True)
        help_document("aifunc/request_info")
        st.divider()

        # result code panel
        st.subheader(_("Func Result"))
        st.caption(generate_import_path(result_type))
        source = inspect.getsource(result_type)
        st.code(source, line_numbers=True, wrap_lines=True)
        st.divider()

        # run
        st.subheader(_("Usage Example"))
        markdown_document("aifunc/usage_example")

        # full context
        st.subheader(_("AIFunc Full Context"))
        with st.expander(module_name):
            source = inspect.getsource(mod)
            st.code(source, line_numbers=True, wrap_lines=True)
        st.divider()
