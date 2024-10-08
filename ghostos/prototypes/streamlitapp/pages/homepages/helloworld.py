import streamlit as st
from ghostos.container import Container
from ghostos.prototypes.streamlitapp.utils.session import Singleton

st.write("hello world!")
container = Singleton.get(Container, st.session_state)
st.write(str(container))
