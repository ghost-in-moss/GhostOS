import streamlit as st
from ghostos.prototypes.streamlitapp.utils.route import Router
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.prototypes.streamlitapp.resources import get_app_docs, get_app_conf


def application_navigator_menu():
    router = Singleton.get(Router, st.session_state)
    menu = router.default_antd_menu_items()
    route = router.render_antd_menu(menu)
    if route and route.label() != route.current_page_label():
        route.switch_page()


@st.dialog(title="Code", width="large")
def open_code_dialog(title: str, code: str):
    st.subheader(title)
    st.code(code, line_numbers=True, wrap_lines=True)


def help_document(doc_name: str, label="help"):
    is_helping = get_app_conf().BoolOpts.HELP_MODE.get()
    with st.expander(label=label, expanded=is_helping):
        doc = get_app_docs().read(doc_name)
        st.markdown(doc, unsafe_allow_html=True)


def markdown_document(doc_name: str, **kwargs):
    doc = get_app_docs().read(doc_name)
    if kwargs:
        doc = doc.format(**kwargs)
    st.markdown(doc, unsafe_allow_html=True)
