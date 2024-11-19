import streamlit as st
from typing import Iterable
from ghostos.core.messages import Message, Role, MessageType
from ghostos.prototypes.streamlitapp.resources import get_app_conf
from ghostos.helpers import gettext as _


def render_messages(messages: Iterable[Message]):
    debug = get_app_conf().BoolOpts.DEBUG_MODE.get()
    for msg in messages:
        render_message_item(msg, debug=debug)


def render_message_item(msg: Message, debug: bool):
    if not msg.is_complete():
        return
    if MessageType.ERROR.match(msg):
        with st.chat_message("user"):
            st.caption(_("Error"))
            st.error(msg.get_content())
        return
    if msg.role == Role.ASSISTANT.value:
        render_ai_message(msg, debug)
    elif msg.role == Role.USER.value:
        render_user_message(msg, debug)
    elif msg.role == Role.SYSTEM.value:
        render_sys_message(msg, debug)
    elif msg.role == Role.FUNCTION.value:
        render_func_message(msg, debug)
    else:
        render_other_message(msg, debug)


def render_ai_message(msg: Message, debug: bool):
    content = msg.content
    if not content:
        return
    replacements = {
        "<code>": "\n```python\n",
        "</code>": "\n```\n",
        "<moss>": "\n```python\n",
        "</moss>": "\n```\n",
    }
    for key, value in replacements.items():
        content = content.replace(key, value)

    with st.chat_message("ai"):
        if msg.type:
            st.caption(msg.type)
        if msg.name:
            st.caption(msg.name)
        st.markdown(content, unsafe_allow_html=True)
    if debug:
        render_msg_debug(msg)


def render_msg_debug(msg: Message):
    with st.expander(label=_("debug"), expanded=False):
        st.json(msg.model_dump_json(exclude_defaults=True, indent=2))


def render_user_message(msg: Message, debug: bool):
    content = msg.get_content()
    with st.chat_message("user"):
        if msg.name:
            st.caption(msg.name)
        if msg.type:
            st.caption(msg.type)
        st.markdown(content, unsafe_allow_html=True)


def render_sys_message(msg: Message, debug: bool):
    content = msg.content
    with st.chat_message("user"):
        st.caption("system message")
        st.markdown(content, unsafe_allow_html=True)
    if debug:
        render_msg_debug(msg)


def render_func_message(msg: Message, debug: bool):
    content = msg.content
    with st.expander(_("function"), expanded=False):
        if msg.name:
            st.caption(msg.name)
        st.markdown(content, unsafe_allow_html=True)
    if debug:
        render_msg_debug(msg)


def render_other_message(msg: Message, debug: bool):
    content = msg.content
    with st.expander(_("other"), expanded=False):
        if msg.name:
            st.caption(msg.name)
        st.markdown(content, unsafe_allow_html=True)
    if debug:
        render_msg_debug(msg)
