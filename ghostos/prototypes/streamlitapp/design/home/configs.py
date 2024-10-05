import streamlit as st

st.set_page_config(
    page_title="GhostOS",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!",
    }
)

st.markdown("# hello world", unsafe_allow_html=True)
