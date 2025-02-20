import streamlit as st
from typing import Iterable
import time

if "run" not in st.session_state:
    st.session_state["run"] = 1
run = st.session_state["run"]
st.write(run)


class Output:
    def __init__(self):
        self.content: str = ""

    def iter_content(self) -> Iterable[str]:
        passed = 0
        while True:
            if passed > 500:
                break
            self.content += "hello"
            yield "hello"
            time.sleep(0.1)
            passed += 1


if "output" not in st.session_state:
    st.session_state["output"] = Output()
output = st.session_state["output"]

with st.chat_message("ai"):
    st.write(output.content)

recorded = 0
if "recorded" in st.session_state:
    recorded = st.session_state["recorded"]
st.write("recorded: %d" % recorded)
if recorded == 0:
    if audio := st.audio_input("Audio file", key=f"{run}-audio-input"):
        st.write(audio)
        recorded = len(audio.getvalue())
        st.session_state["recorded"] = recorded
        st.rerun()
else:
    if st.button("stop"):
        run += 1
        st.session_state["run"] = run
        st.session_state["recorded"] = 0
        st.rerun()
    with st.empty():
        st.write(output.iter_content())
        st.write("done")
