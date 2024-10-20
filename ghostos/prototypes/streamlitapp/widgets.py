import streamlit as st
from typing import List, Union, Dict, Iterable, Tuple, Optional
import streamlit_antd_components as sac
from ghostos.core.aifunc import ExecFrame, ExecStep
from ghostos.core.messages import Message, Role, DefaultMessageTypes
from ghostos.core.moss import PyContext
from ghostos.prototypes.streamlitapp.utils.route import Router
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.prototypes.streamlitapp.resources import get_app_docs, get_app_conf
from ghostos.helpers import gettext as _


def application_navigator_menu():
    router = Singleton.get(Router, st.session_state)
    menu = router.default_antd_menu_items()
    route = router.render_antd_menu(menu)
    if route and route.label() != route.current_page_label():
        route.switch_page()


@st.dialog(title=_("Code"), width="large")
def open_code_dialog(title: str, code: str):
    st.subheader(title)
    st.code(code, line_numbers=True, wrap_lines=True)


def help_document(doc_name: str, label="help"):
    is_helping = get_app_conf().BoolOpts.HELP_MODE.get()
    with st.expander(label=label, expanded=is_helping):
        doc = get_app_docs().read(doc_name)
        st.markdown(doc, unsafe_allow_html=True)


def markdown_document(doc_name: str, **kwargs):
    doc = get_app_docs().read(doc_name)
    if kwargs:
        doc = doc.format(**kwargs)
    st.markdown(doc, unsafe_allow_html=True)


def get_exec_label_bloodline(label: str) -> List[int]:
    splits = label.split("|", 2)
    if len(splits) == 1:
        return []
    return [int(c) for c in splits[1].split("_")]


def render_messages(messages: Iterable[Message]):
    debug = get_app_conf().BoolOpts.DEBUG_MODE.get()
    for msg in messages:
        render_message(msg, debug=debug)


def render_message(msg: Message, debug: bool):
    if not msg.is_complete():
        return
    if DefaultMessageTypes.ERROR.match(msg):
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


def flatten_exec_frame_tree(frame: ExecFrame) -> Dict[str, Union[ExecFrame, ExecStep]]:
    def iter_frame(fr: ExecFrame, bloodline: List[int]) -> Iterable[Tuple[str, Union[ExecFrame, ExecStep]]]:
        yield __frame_label(fr, bloodline), fr
        idx = 0
        for step in fr.steps:
            idx += 1
            next_bloodline = bloodline.copy()
            next_bloodline.append(idx)
            yield from iter_step(step, next_bloodline)

    def iter_step(step: ExecStep, bloodline: List[int]) -> Iterable[Tuple[str, Union[ExecStep, ExecFrame]]]:
        yield __step_label(step, bloodline), step
        idx = 0
        for fra in step.frames:
            idx += 1
            next_bloodline = bloodline.copy()
            next_bloodline.append(idx)
            yield from iter_frame(fra, next_bloodline)

    result = {}
    for key, value in iter_frame(frame.model_copy(), []):
        result[key] = value
    return result


def render_exec_frame_tree(label: str, frame: ExecFrame):
    root = build_exec_frame_tree_node(frame.model_copy(), [])
    return sac.tree(
        [root],
        label=label,
        size="lg",
        open_all=True,
        show_line=True,
    )


def build_exec_frame_tree_node(frame: ExecFrame, bloodline: List[int]) -> sac.TreeItem:
    children = []
    if len(bloodline) < 20:
        steps = frame.steps
        idx = 0
        for step in steps:
            idx += 1
            next_bloodline = bloodline.copy()
            next_bloodline.append(idx)
            step_node = build_exec_step_tree_node(step, next_bloodline)
            children.append(step_node)
    return sac.TreeItem(
        label=__frame_label(frame, bloodline),
        icon="stack",
        tooltip=f"click to see the frame details",
        children=children,
    )


def build_exec_step_tree_node(step: ExecStep, bloodline: List[int]) -> sac.TreeItem:
    children = []
    if len(bloodline) < 20:
        idx = 0
        for frame in step.frames:
            idx += 1
            next_bloodline = bloodline.copy()
            next_bloodline.append(idx)
            frame_node = build_exec_frame_tree_node(frame, next_bloodline)
            children.append(frame_node)
    return sac.TreeItem(
        __step_label(step, bloodline),
        icon="circle" if len(children) == 0 else "plus-circle",
        tooltip=f"click to see the step details",
        children=children,
    )


def __frame_label(frame: ExecFrame, bloodline: List[int]) -> str:
    suffix = ""
    if len(bloodline) > 0:
        suffix = "__" + "_".join([str(c) for c in bloodline])
    return frame.func_name() + suffix


def __step_label(step: ExecStep, bloodline: List[int]) -> str:
    suffix = ""
    if len(bloodline) > 0:
        suffix = "__" + "_".join([str(c) for c in bloodline])
    return step.func_name() + suffix


def render_pycontext(pycontext: PyContext):
    if not pycontext:
        return
    st.subheader("PyContext")
    if pycontext.module:
        st.caption(f"module: {pycontext.module}")
    if pycontext.code:
        with st.expander(_("Code"), expanded=True):
            st.code(pycontext.code)
    if pycontext.execute_code:
        with st.expander(_("Execute"), expanded=True):
            st.code(pycontext.execute_code)
        st.write(f"executed: {pycontext.executed}")
    st.divider()
