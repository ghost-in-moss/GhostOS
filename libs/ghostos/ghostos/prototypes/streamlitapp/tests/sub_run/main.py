from streamlit.web.cli import main_run
from os.path import dirname, join
import streamlit as st

hello = "world"

if __name__ == "__main__":
    hello = "hello"
    st.session_state["hello"] = "hello"
    filename = join(dirname(__file__), "page.py")
    print("++++++++++++", filename)
    main_run([filename, "hello world", "who are your daddy", "--logger.enableRich=True"] )
