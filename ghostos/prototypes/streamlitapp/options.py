import streamlit as st
from typing import Optional
from enum import Enum


class BoolOpts(str, Enum):

    HELP_MODE = "ghostos.streamlit.app.help_mode"
    """global help mode"""

    DEBUG_MODE = "ghostos.streamlit.app.debug_mode"

    def set(self, val: bool) -> None:
        st.session_state[self.value] = val

    def get(self) -> bool:
        key = self.value
        return key in st.session_state and st.session_state[self.value] is True

    def toggle(self) -> None:
        st.session_state[self.value] = not self.get()

    def render_toggle(
            self,
            label: str, *,
            tips: Optional[str] = None,
            disabled: bool = False,
    ) -> None:
        st.toggle(
            label,
            key=self.value,
            disabled=disabled,
            help=tips,
        )

    def render_button(
            self,
            label: str, *,
            tips: Optional[str] = None,
            disabled: bool = False,
    ) -> bool:
        return st.button(
            label,
            key=self.value,
            disabled=disabled,
            help=tips,
        )
