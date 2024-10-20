import streamlit as st
from ghostos.container import Container




def main(con: Container):
    st.navigation([
        st.Page('page.py', title='Page'),
    ])
