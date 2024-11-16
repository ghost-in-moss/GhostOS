import streamlit as st
from ghostos.prototypes.streamlitapp.tests.sub_run.main import hello
import sys

st.write(sys.argv)
st.write(hello)
if "hello" in st.session_state:
    st.title(st.session_state["hello"])
