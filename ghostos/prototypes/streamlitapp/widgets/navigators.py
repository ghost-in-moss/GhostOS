import streamlit as st
from ghostos.prototypes.streamlitapp.utils.route import Router
from ghostos.prototypes.streamlitapp.utils.session import Singleton


def application_navigator_menu():
    router = Singleton.get(Router, st.session_state)
    menu = router.default_antd_menu_items()
    route = router.render_antd_menu(menu)
    if route and route.label() != route.current_page_label():
        route.switch_page()
