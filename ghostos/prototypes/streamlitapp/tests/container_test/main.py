import streamlit as st
from ghostos_container import Container




def main(con: Container):
    st.navigation([
        st.Page('page.py', title='Page'),
    ])
