import streamlit as st

pages = st.navigation(
    [
        st.Page('homepage/home.py', title="Home", default=True),
        st.Page('homepage/host.py'),
        st.Page('homepage/applications.py'),
        st.Page('aifuncs/index.py'),
        st.Page('aifuncs/details.py'),
    ],
    position="hidden",
)


with st.sidebar:
    st.page_link(
        "homepage/home.py",
        label="Home",
        icon=":material/home:",
    )
# st.page_link(
#     "homepage/home.py",
#     label="Home",
#     icon=":material/home:",
#     help="GhostOS homepage",
# )
# st.page_link(
#     "homepage/applications.py",
#     label="Applications",
#     icon=":material/apps:",
# )

pages.run()
