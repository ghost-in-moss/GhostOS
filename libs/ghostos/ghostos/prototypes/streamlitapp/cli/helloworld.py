import streamlit as st
from ghostos.prototypes.streamlitapp.main import main_run, Singleton
from sys import argv

if len(argv) < 2:
    raise SystemExit("invalid arguments")

argument = argv[1]

st.title("Hello World")
st.write(argument)
