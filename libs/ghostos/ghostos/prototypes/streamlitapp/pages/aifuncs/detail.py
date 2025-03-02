from typing import Type
import streamlit as st
import streamlit_react_jsonschema as srj
from ghostos.prototypes.streamlitapp.pages.router import AIFuncListRoute, AIFuncDetailRoute
from ghostos.prototypes.streamlitapp.resources import (
    get_container,
)
from ghostos.prototypes.streamlitapp.widgets.docs import (
    help_document, markdown_document,
)
from ghostos.prototypes.streamlitapp.widgets.exec_frame import (
    render_exec_frame_tree,
    flatten_exec_frame_tree,
)
from ghostos.prototypes.streamlitapp.widgets.moss import render_pycontext
from ghostos.prototypes.streamlitapp.widgets.messages import (
    render_message_item,
    render_messages,
)
from ghostos.core.messages import new_basic_connection
from ghostos.core.aifunc import (
    AIFunc,
    AIFuncExecutor,
    get_aifunc_result_type,
    ExecFrame, ExecStep,
)
from ghostos_common.identifier import Identifier, identify_class
from ghostos_common.helpers import (
    uuid,
    gettext as _,
    import_from_path,
    import_class_from_path, generate_import_path,
    parse_import_path_module_and_attr_name,
    Timeleft,
)
import inspect
import webbrowser
from threading import Thread


def render_sidebar():
    with st.sidebar:
        AIFuncListRoute().render_page_link(use_container_width=True)


def render_header(fn: Type[AIFunc]) -> Identifier:
    idt = identify_class(fn)
    # 渲染全局信息.
    st.title(idt.name)
    st.caption(idt.id)
    st.markdown(idt.description)
    return idt


def render_source(route: AIFuncDetailRoute, fn: Type[AIFunc]):
    # prepare
    module_name, attr_name = parse_import_path_module_and_attr_name(route.aifunc_id)
    mod = import_from_path(module_name)
    result_type = get_aifunc_result_type(fn)
    idt = identify_class(fn)

    # open source code
    if st.button("Open The Source File"):
        webbrowser.open(f"file://{mod.__file__}")

    # func code panel
    st.subheader(_("Func Request"))
    st.caption(idt.id)
    source = inspect.getsource(fn)
    st.code(source, line_numbers=True, wrap_lines=True)
    help_document("aifunc/request_info")
    st.divider()

    # result code panel
    st.subheader(_("Func Result"))
    st.caption(generate_import_path(result_type))
    source = inspect.getsource(result_type)
    st.code(source, line_numbers=True, wrap_lines=True)
    st.divider()

    # run
    st.subheader(_("Usage Example"))
    markdown_document("aifunc/usage_example")

    # full context
    st.subheader(_("AIFunc Full Context"))
    with st.expander(module_name):
        source = inspect.getsource(mod)
        st.code(source, line_numbers=True, wrap_lines=True)


def render_aifunc_execute_stream(route: AIFuncDetailRoute, fn: Type[AIFunc]):
    route.clear_execution()
    # render form
    with st.expander(_("Request"), expanded=True):
        args, submitted = srj.pydantic_form(fn, key=route.aifunc_id)
    if not submitted or not args:
        return
    if not isinstance(args, AIFunc):
        st.error(f"Expected an AIFunc instance, got {type(args)}")
        return

    executor = get_container().force_fetch(AIFuncExecutor)
    stream, receiver = new_basic_connection(timeout=route.timeout, idle=route.exec_idle, complete_only=True)
    frame, caller = executor.new_exec_frame(args, stream)
    # save status
    route.frame = frame
    route.executed = True
    route.bind(st.session_state)

    # render
    timeleft = Timeleft(route.timeout)
    t = Thread(target=caller)
    t.start()
    with st.status(_("executing...")):
        with receiver:
            for item in receiver.recv():
                if not item.is_complete():
                    continue
                route.received.append(item)
                render_message_item(item, debug=False)
    st.write(f"executed in {round(timeleft.passed(), 2)} seconds")


def render_aifunc_frame_tail(frame: ExecFrame):
    if not frame:
        return
    # error
    if frame.error:
        st.error(frame.error.get_content())

    result = frame.get_result()
    if result:
        with st.expander("Exec Result", expanded=True):
            key = "AIFuncResult_" + uuid()
            srj.pydantic_instance_form(result, readonly=True, key=key)

    if frame.steps:
        st.caption(f"{len(frame.steps)} steps ran")

    with st.expander("origin data", expanded=False):
        st.json(frame.model_dump_json(indent=2, exclude_defaults=True))


def render_aifunc_frame_stack(frame: ExecFrame):
    if not frame:
        return
    selected = render_exec_frame_tree(_("Exec Stack"), frame)
    # open dialog
    if selected:
        mapping = flatten_exec_frame_tree(frame)
        selected_item = mapping.get(selected, None)
        if isinstance(selected_item, ExecFrame):
            open_exec_frame_dialog(selected_item)
        elif isinstance(selected_item, ExecStep):
            open_exec_step_dialog(selected_item)


def render_aifunc_executed_frame_head(frame: ExecFrame):
    if not frame:
        return
    args = frame.get_args()
    # render form
    with st.expander(_("Request"), expanded=True):
        key = "AIFuncRequest_" + uuid()
        srj.pydantic_instance_form(args, readonly=True, key=key)


def render_aifunc_exec_step(step: ExecStep):
    if step.pycontext:
        render_pycontext(step.pycontext)

    if step.error:
        with st.expander(_("Error"), expanded=True):
            st.error(step.error.get_content())

    with st.expander(label=_("History"), expanded=True):
        render_messages(step.iter_messages(), debug=False, in_expander=True)

    if step.frames:
        st.caption(f"{len(step.frames)} frames called")

    with st.expander("origin data", expanded=False):
        st.json(step.model_dump_json(indent=2, exclude_defaults=True))


@st.dialog(title=_("ExecStep"), width="large")
def open_exec_step_dialog(step: ExecStep):
    st.subheader(step.func_name())
    st.caption(f"step_id: {step.step_id}")
    render_aifunc_exec_step(step)


@st.dialog(title=_("ExecFrame"), width="large")
def open_exec_frame_dialog(exec_frame: ExecFrame):
    st.subheader(exec_frame.func_name())
    st.caption(f"frame_id: {exec_frame.frame_id}")
    render_aifunc_executed_frame_head(exec_frame)

    with st.expander(label=_("History"), expanded=False):
        idx = 0
        for step in exec_frame.steps:
            st.caption(f"step {idx}")
            render_messages(step.iter_messages(), debug=False, in_expander=True)
            idx = idx + 1

    render_aifunc_frame_tail(exec_frame)


def main():
    route = AIFuncDetailRoute().get_or_bind(st.session_state)
    render_sidebar()

    if not route.aifunc_id:
        st.error(f"AI Function {route.aifunc_id} found")
        return
    try:
        fn = import_class_from_path(route.aifunc_id, AIFunc)
    except TypeError as e:
        st.error(e)
        return

    # render header
    render_header(fn)

    tab_exec, tab_source = st.tabs([_("Execute AIFuncs"), _("Source Code")])
    with tab_exec:
        if not route.executed:
            render_aifunc_execute_stream(route, fn)
            render_aifunc_frame_tail(route.frame)
            render_aifunc_frame_stack(route.frame)
        elif route.frame:
            render_aifunc_executed_frame_head(route.frame)
            with st.expander(label=_("messages"), expanded=True):
                render_messages(route.received, debug=False, in_expander=True)

            if route.frame:
                render_aifunc_frame_tail(route.frame)
                render_aifunc_frame_stack(route.frame)

        if route.executed:
            if st.button(_("rerun?")):
                route.clear_execution()
                route.bind(st.session_state)
                st.rerun()

    with tab_source:
        render_source(route, fn)
