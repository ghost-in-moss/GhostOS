import streamlit as st
from enum import Enum


class Bool(str, Enum):
    HELP_MODE = "ghostos.streamlit.app.help_mode"
    """global help mode"""

    def set(self, val: bool) -> None:
        st.session_state[self.value] = val

    def get(self) -> bool:
        key = self.value
        return key in st.session_state and st.session_state[self.value] is True

    def toggle(self) -> None:
        st.session_state[self.value] = not self.get()
