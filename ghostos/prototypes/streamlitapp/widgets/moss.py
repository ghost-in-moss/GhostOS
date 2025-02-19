import streamlit as st
from ghostos_moss import PyContext
from ghostos_common.helpers import gettext as _


def render_pycontext(pycontext: PyContext):
    if not pycontext:
        return
    st.subheader("PyContext")
    if pycontext.module:
        st.caption(f"module: {pycontext.module}")
    if pycontext.code:
        with st.expander(_("Code"), expanded=True):
            st.code(pycontext.code)
    if pycontext.execute_code:
        with st.expander(_("Execute"), expanded=True):
            st.code(pycontext.execute_code)
        st.write(f"executed: {pycontext.executed}")
    st.divider()
