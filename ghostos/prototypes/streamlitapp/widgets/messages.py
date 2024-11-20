import streamlit as st
from typing import Iterable, List, NamedTuple
from ghostos.core.messages import Message, Role, MessageType, Caller
from ghostos.helpers import gettext as _


class MessageGroup(NamedTuple):
    msg_name: str
    msg_role: str
    stage: str
    messages: List[Message]


def render_messages(messages: Iterable[Message], debug: bool):
    groups: List[MessageGroup] = []
    group = MessageGroup("", "", "", [])

    for msg in messages:
        if not msg.is_complete():
            continue
        if msg.name != group.msg_name or msg.role != group.msg_role or msg.stage != group.stage:
            if group.messages:
                groups.append(group)
            group = MessageGroup(msg.name, msg.role, msg.stage, [])
        group.messages.append(msg)

    if group.messages:
        groups.append(group)
    for group in groups:
        render_message_group(group, debug)


def render_message_group(group: MessageGroup, debug: bool):
    role = group.msg_role
    name = group.msg_name
    stage = group.stage
    caption = f"{role}: {name}" if name else role
    render_role = "user" if role == Role.USER.value else "assistant"
    if stage:
        with st.container(border=True):
            st.caption(stage)
            with st.chat_message(render_role):
                st.caption(caption)
                for msg in group.messages:
                    render_message_content(msg, debug)
    else:
        with st.chat_message(render_role):
            st.caption(caption)
            for msg in group.messages:
                render_message_content(msg, debug)


def render_message_content(message: Message, debug: bool):
    if message.type == MessageType.ERROR:
        st.error(f"Error: {message.content}")
    elif MessageType.is_text(message):
        st.markdown(message.content)
    # todo: more types
    else:
        st.write(message.model_dump(exclude_defaults=True))

    if message.callers:
        if st.button("tool calls", key="tool calls" + message.msg_id):
            open_message_caller(message)


@st.dialog("message_caller")
def open_message_caller(message: Message):
    for caller in message.callers:
        st.write(caller.model_dump(exclude_defaults=True))


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
