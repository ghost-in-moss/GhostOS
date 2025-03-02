from typing import Iterable
import streamlit as st
import time


def get_content() -> Iterable[str]:
    content = "hello world"
    for c in content:
        yield c
        time.sleep(0.05)


for i in range(5):
    with st.empty():
        with st.chat_message("ai"):
            st.write_stream(get_content())
        with st.chat_message("ai"):
            st.write("hello world!!")
