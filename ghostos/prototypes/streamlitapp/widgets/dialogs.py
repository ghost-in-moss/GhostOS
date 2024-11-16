import streamlit as st
from ghostos.helpers import gettext as _


@st.dialog(title=_("Code"), width="large")
def open_code_dialog(title: str, code: str):
    st.subheader(title)
    st.code(code, line_numbers=True, wrap_lines=True)
