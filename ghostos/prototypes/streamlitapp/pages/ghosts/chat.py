import streamlit as st
import time
import streamlit_react_jsonschema as srj
from typing import Iterable, List
from ghostos.prototypes.streamlitapp.pages.router import (
    GhostChatRoute,
)
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.prototypes.streamlitapp.widgets.messages import (
    render_message_in_content, render_message_payloads
)
from ghostos.prototypes.streamlitapp.widgets.renderer import (
    render_object, render_event, render_turn,
    render_empty,
)
from ghostos.prototypes.streamlitapp.resources import get_app_conf
from ghostos.core.runtime import GoThreadInfo, Event, GoTaskStruct
from ghostos.core.messages import Receiver, Role, ReceiverBuffer, MessageType, Message
from streamlit.logger import get_logger
from ghostos.abcd import Shell, Conversation, Context
from ghostos.identifier import get_identifier
from ghostos.helpers import gettext as _
from ghostos.helpers import generate_import_path, yaml_pretty_dump
from pydantic import BaseModel
import inspect

logger = get_logger("ghostos")


def main():
    # create shell
    route = GhostChatRoute.get(st.session_state)
    if route is None:
        st.error("No route found for session state")
        return

    # get ghost and context
    ghost = route.get_ghost()
    context = route.get_context()
    ghost = route.get_route_bound(ghost)
    context = route.get_route_bound(context)

    conversation = Singleton.get(Conversation, st.session_state, force=False)
    if not conversation:
        shell = Singleton.get(Shell, st.session_state)
        # create conversation
        conversation = shell.sync(ghost, context)
        Singleton(conversation, Conversation).bind(st.session_state)
    # run the pages
    run_chat_page(route, conversation)
    route.get_or_bind(st.session_state)


def run_chat_page(route: GhostChatRoute, conversation: Conversation):
    pic = None
    with st.sidebar:
        # other pages
        if st.button(_("Ghost Settings"), use_container_width=True):
            render_ghost_settings(route)
        if st.button(_("Context"), use_container_width=True):
            render_context_settings(conversation)
        if st.button("Task Info", use_container_width=True):
            render_task_info_settings(conversation.task())
        if st.button("Clear Messages", use_container_width=True):
            thread = conversation.thread()
            thread = thread.reset_history([])
            conversation.update_thread(thread)
            st.rerun()

        st.subheader("Inputs")
        # input type
        with st.container(border=True):
            auto_run = st.toggle(
                "auto run event",
                help="automatic run background event",
                value=True,
            )
            show_video = st.toggle("show video")
            show_image_file = st.toggle("upload image")

        if show_video:
            pic = st.camera_input("Task a picture")
        if show_image_file:
            image = st.file_uploader("Upload image", type=["png", "jpg", "jpeg"])
        for i in range(5):
            st.empty()

    # header
    st.title("Ghost")
    ghost = route.get_ghost()
    id_ = get_identifier(ghost)
    import_path = generate_import_path(ghost.__class__)
    data = {
        _("name"): id_.name,
        _("desc"): id_.description,
        _("class"): import_path,
    }
    # description
    st.markdown(f"""
```yaml
{yaml_pretty_dump(data)}
```
""")
    inputs = []
    if chat_input := st.chat_input("message"):
        inputs = route.get_route_bound([], "inputs")
        inputs.append(Role.USER.new(chat_input))
        route.bind_to_route([], "inputs")
        route.input_type = ""

    chatting(route, conversation, inputs, auto_run)


def chatting(route: GhostChatRoute, conversation: Conversation, inputs: List[Message], rotate: bool):
    thread = conversation.thread()
    render_thread_messages(thread, max_turn=20)
    debug = get_app_conf().BoolOpts.DEBUG_MODE.get()
    render_empty()

    if inputs:
        event, receiver = conversation.respond(inputs)
        render_event(event, debug)
        render_receiver(receiver, debug)

    while not route.input_type and rotate and not conversation.closed():
        if event := conversation.pop_event():
            render_event(event, debug)
            receiver = conversation.respond_event(event)
            render_receiver(receiver, debug)
        else:
            time.sleep(1)


@st.dialog("Textarea")
def video_input_dialog(route: GhostChatRoute):
    text = st.text_area("You message", value="")
    logger.debug("++++++++++++++++ set chat_text_input: %s", text)
    if text:
        st.session_state["chat_text_input"] = text
    logger.debug("end of text area input")


def render_receiver(receiver: Receiver, debug: bool):
    try:
        with receiver:
            with st.status("waiting..."):
                buffer = ReceiverBuffer.new(receiver.recv())
            if buffer is None:
                return
            with st.chat_message("assistant"):
                while buffer is not None:
                    if MessageType.is_text(buffer.head()):
                        contents = chunks_to_st_stream(buffer.chunks())
                        st.write_stream(contents)
                        render_message_payloads(buffer.tail(), debug)
                    else:
                        render_message_in_content(buffer.tail(), debug)
                    # render next item
                    buffer = buffer.next()
    except Exception as e:
        st.exception(e)


def chunks_to_st_stream(chunks: Iterable[Message]) -> Iterable[str]:
    for chunk in chunks:
        if chunk.content:
            yield chunk.content


@st.dialog(_("Ghost Settings"), width="large")
def render_ghost_settings(route: GhostChatRoute):
    if route is None:
        st.error("page is not configured")
        return
    ghost = route.get_ghost()
    # render ghost info
    if isinstance(ghost, BaseModel):
        data, mod = srj.pydantic_instance_form(ghost)
        if st.button("Save"):
            st.write("todo saving ghosts")
    else:
        st.write(ghost)
    source = inspect.getsource(ghost.__class__)
    with st.expander("source code", expanded=False):
        st.code(source)
    render_empty()


@st.dialog("Ghost Context", width="large")
def render_context_settings(conversation: Conversation):
    ctx = conversation.get_context()
    ghost = conversation.get_ghost()
    if ctx is None and ghost.ContextType is None:
        st.info("No specific Context for this Ghost")
        return
    if ctx is None:
        if ghost.ContextType is not None:
            data, submitted = srj.pydantic_form(ghost.ContextType)
            if submitted and isinstance(data, Context):
                conversation.update_context(data)
                ctx = data
    else:
        data, changed = render_object(ctx, immutable=False)
        if changed and isinstance(data, Context):
            conversation.update_context(data)
            ctx = data

    # render prompt
    if ctx is not None:
        st.subheader(_("Context prompt"))
        try:
            prompt = ctx.get_prompt(conversation.container())
            st.markdown(prompt)
        except Exception as e:
            st.error(e)
    # render artifact
    if ghost.ArtifactType:
        st.subheader(_("Artifact"))
        artifact = conversation.get_artifact()
        render_object(artifact)
    render_empty()


@st.dialog("Task Info", width="large")
def render_task_info_settings(task: GoTaskStruct):
    from ghostos.core.runtime.tasks import TaskBrief
    brief = TaskBrief.from_task(task)
    srj.pydantic_instance_form(brief, readonly=True)

    with st.expander(_("Detail"), expanded=False):
        st.write(task.model_dump(exclude_defaults=True))
    render_empty()


def render_thread_messages(thread: GoThreadInfo, max_turn: int = 20):
    turns = list(thread.turns())
    turns = turns[-max_turn:]
    debug = get_app_conf().BoolOpts.DEBUG_MODE.get()
    count = 0
    for turn in turns:
        count += render_turn(turn, debug)
    if count == 0:
        st.info("No thread messages yet")


def render_event_object(event: Event, debug: bool):
    if event is None:
        return
    from_task_name = event.from_task_name
    if debug and from_task_name is not None:
        st.button(f"from task {from_task_name}", key=f"from task {event.event_id}")
