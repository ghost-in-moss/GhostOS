import streamlit as st
import time
from typing import List, Iterator
from ghostos.prototypes.streamlitapp.utils.route import Route, Link


class ChatRoute(Route):
    link = Link(
        name="chat",
        import_path="path",
    )
    messages: List[str] = []
    input: str = ""
    disabled: bool = False
    buffer: str = ""

    def set_input(self):
        i = st.session_state["t_inputs"]
        self.input = i

    def iter_messages(self) -> Iterator[str]:
        for line in self.messages:
            yield line
        if self.buffer:
            self.messages.append(self.buffer)
            buffer = self.buffer
            self.buffer = ""
            yield buffer

    def iter_output(self, line: str) -> Iterator[str]:
        self.buffer = ""
        for c in line:
            self.buffer += c
            yield c
            if self.input:
                break
            time.sleep(0.2)


chat = ChatRoute().get_or_bind(st.session_state)


@st.fragment
def run_messages():
    count = 0
    for msg in chat.iter_messages():
        role = "ai"
        if msg.startswith("user:"):
            role = "user"
        with st.chat_message(role):
            st.write(msg)
            with st.expander("debug mode", expanded=False):
                st.write("hello")

    while True:
        if i := chat.input:
            content = f"user:{i}"
            chat.input = ""
            with st.chat_message("user"):
                st.write(content)
                chat.messages.append(content)
        count += 1
        if count % 30 == 0:
            chat.disabled = True
            content = f"another round {count}"
            with st.chat_message("ai"):
                items = chat.iter_output(content)
                st.write_stream(items)
                chat.messages.append(content)
            chat.disabled = False
        time.sleep(0.1)


if i := st.chat_input("input"):
    chat.input = i

run_messages()
