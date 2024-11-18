import streamlit as st
from ghostos.prototypes.streamlitapp.pages.router import GhostChatPage
from ghostos.identifier import get_identifier
from ghostos.helpers import gettext as _


def main():
    ghost_chat_page = GhostChatPage.get_or_bind(st.session_state)
    ghost = ghost_chat_page.get_ghost()
    id_ = get_identifier(ghost)

    input_type = "chat"
    with st.sidebar:
        st.button("Chat", type="primary", icon=":material/chat:", use_container_width=True)
        if st.button("Image Input", use_container_width=True):
            input_type = "image"
        if st.button("Textarea Input", use_container_width=True):
            input_type = "text"
        if st.button("File Input", use_container_width=True):
            input_type = "file"
        st.button("Video Shortcut Input", use_container_width=True)
        st.divider()
        st.button("Ghost Setting", type="secondary", use_container_width=True)
        if st.button("Context Setting", type="secondary", use_container_width=True):
            open_test_dialog()
        st.button("Task Info", type="secondary", use_container_width=True)
        st.button("Thread Info", type="secondary", use_container_width=True)
        st.button("Subtasks", type="secondary", use_container_width=True)

    st.subheader(_("You are talking to: ") + id_.name)
    if id_.description:
        st.caption(id_.description)

    for i in range(10):
        with st.chat_message("assistant"):
            st.write("hello world")

    if input_type == "chat":
        if inputs := st.chat_input():
            st.write(inputs)
    elif input_type == "image":
        if inputs := st.file_uploader("Choose an image...", type="jpg"):
            st.write(inputs)


@st.dialog("test")
def open_test_dialog():
    st.write("hello world")
