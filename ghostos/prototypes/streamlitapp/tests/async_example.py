import streamlit as st
import time

st.title("Test")


@st.fragment
def messages():
    count = 0
    while "run" not in st.session_state or st.session_state["run"] is True:
        count += 1
        with st.chat_message("ai"):
            st.write(f"Hello world! {count}")
        time.sleep(1)


# st.toggle(label="run", key="run", value=True)

def callback():
    st.session_state["run"] = False


st.chat_input("test", on_submit=callback)
messages()
