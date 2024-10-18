import streamlit as st
from random import randint

st.write(randint(0, 1000))

if value := st.button("test render"):
    # always set same value, see if the session trigger rendering
    st.write("button: " + str(value))
    st.session_state["some"] = dict(foo="bar")
