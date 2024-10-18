import streamlit as st
from ghostos.prototypes.streamlitapp.navigation import AIFuncListRoute
from ghostos.prototypes.streamlitapp.resources import trans as _


def aifuncs_list():
    # bind if route value not bind before
    route = AIFuncListRoute().get_or_bind(st.session_state)
    st.title(_("AI functions"))
