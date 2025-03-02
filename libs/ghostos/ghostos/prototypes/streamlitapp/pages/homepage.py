from ghostos_common.helpers import gettext as _


def home():
    import streamlit as st
    from ghostos.prototypes.streamlitapp.widgets.navigators import application_navigator_menu

    st.title(_("GhostOS Homepage"))
    with st.expander(_("App Menu"), expanded=True):
        application_navigator_menu()


def helloworld():
    import streamlit as st
    from ghostos_container import Container
    from ghostos.prototypes.streamlitapp.utils.session import Singleton

    st.write("hello world!")
    container = Singleton.get(Container, st.session_state)
    st.write(str(container))


def navigator():
    import streamlit as st
    from ghostos.prototypes.streamlitapp.utils.route import Router
    from ghostos.prototypes.streamlitapp.utils.session import Singleton

    router = Singleton.get(Router, st.session_state)
    menu = router.default_antd_menu_items()
    route = router.render_antd_menu(menu)
    if route is not None:
        route.switch_page()


def ghostos_host():
    import streamlit as st
    st.title("GhostOS Host")
