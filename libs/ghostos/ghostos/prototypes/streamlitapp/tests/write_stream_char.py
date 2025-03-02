from typing import Iterable
import streamlit as st
import time


def get_content() -> Iterable[str]:
    content = "hello world"
    for c in content:
        yield c
        time.sleep(0.05)


with st.chat_message("ai"):
    for c in get_content():
        st.write_stream([c])
