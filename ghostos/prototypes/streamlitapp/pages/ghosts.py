import streamlit as st
import time
import streamlit_react_jsonschema as srj
from typing import Iterable, List
from ghostos.prototypes.streamlitapp.pages.router import (
    GhostChatRoute, GhostTaskRoute,
)
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.prototypes.streamlitapp.widgets.messages import (
    render_message_in_content
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
from ghostos.entity import to_entity_meta
from ghostos.helpers import gettext as _
from ghostos.helpers import generate_import_path, yaml_pretty_dump
from ghostos.scripts.cli.utils import GhostsConf, GhostInfo
from pydantic import BaseModel
import inspect

logger = get_logger("ghostos")


def main_chat():
    # create shell
    route = GhostChatRoute.get(st.session_state)
    if route is None:
        st.error("No route found for session state")
        return

    # get ghost and context
    conversation = get_conversation(route)
    # run the pages
    with st.sidebar:
        # other pages
        with st.container(border=True):
            GhostTaskRoute().render_page_link(use_container_width=True)
        if st.button("Clear Messages", use_container_width=True):
            thread = conversation.thread()
            thread = thread.reset_history([])
            conversation.update_thread(thread)
            st.rerun()

        st.subheader("chat options")
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
        render_empty()

    # header
    st.title("Ghost")
    with st.container(border=True):
        ghost = route.get_ghost()
        id_ = get_identifier(ghost)
        import_path = generate_import_path(ghost.__class__)
        data = {
            _("name"): id_.name,
            _("desc"): id_.description,
            _("class"): import_path,
        }
        if route.filename:
            data[_("from")] = route.filename
        # description
        st.markdown(f"""
```yaml
{yaml_pretty_dump(data)}
```
""")
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            show_chatting = st.toggle("chat", value=True)
        with col2:
            show_ghost_settings = st.toggle("settings")
        with col3:
            show_instruction = st.toggle("instructions")
        with col4:
            show_context = st.toggle("context")

    # render ghost settings
    if show_ghost_settings:
        render_ghost_settings(route)
    if show_instruction:
        render_instruction(conversation)
    if show_context:
        render_context_settings(conversation)

    # inputs
    if show_chatting:
        st.subheader("Chat")
        inputs = []
        if chat_input := st.chat_input("message"):
            inputs = route.get_route_bound([], "inputs")
            inputs.append(Role.USER.new(chat_input))
            route.bind_to_route([], "inputs")
            route.input_type = ""

        chatting(route, conversation, inputs, auto_run)


def get_conversation(route: GhostChatRoute) -> Conversation:
    conversation = Singleton.get(Conversation, st.session_state, force=False)
    if not conversation or conversation.closed():
        shell = Singleton.get(Shell, st.session_state)
        # create conversation
        conversation = shell.sync(route.get_ghost(), route.get_context())
        Singleton(conversation, Conversation).bind(st.session_state)
    return conversation


def main_task():
    route = GhostChatRoute.get(st.session_state)
    with st.sidebar:
        # other pages
        with st.container(border=True):
            route.render_page_link(use_container_width=True)
    conversation = get_conversation(route)
    task = conversation.task()
    thread = conversation.thread()
    st.title("Ghost Task Info")
    render_task_info_settings(task, thread)


def chatting(route: GhostChatRoute, conversation: Conversation, inputs: List[Message], rotate: bool):
    thread = conversation.thread()
    render_thread_messages(thread, max_turn=20)
    debug = get_app_conf().BoolOpts.DEBUG_MODE.get()

    if inputs:
        event, receiver = conversation.respond(inputs)
        render_event(event, debug)
        render_receiver(receiver, debug)

    while not route.input_type and rotate and conversation.available():
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
            with st.chat_message("assistant"):
                with st.status("waiting..."):
                    buffer = ReceiverBuffer.new(receiver.recv())
                if buffer is None:
                    st.error("No message received")
                    return
                while buffer is not None:
                    if MessageType.is_text(buffer.head()):
                        contents = chunks_to_st_stream(buffer.chunks())
                        with st.empty():
                            st.write_stream(contents)
                            with st.container():
                                render_message_in_content(buffer.tail(), debug)
                    elif MessageType.FUNCTION_CALL.match(buffer.head()):
                        contents = chunks_to_st_stream(buffer.chunks())
                        with st.empty():
                            st.write_stream(contents)
                            with st.container():
                                render_message_in_content(buffer.tail(), debug)
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


def render_ghost_settings(route: GhostChatRoute):
    st.subheader(_("Settings"))
    with st.container(border=True):
        if route is None:
            st.error("page is not configured")
            return
        ghost = route.get_ghost()
        # render ghost info
        if isinstance(ghost, BaseModel):
            data, submitted = srj.pydantic_instance_form(ghost)
            if route.filename and submitted:
                ghosts_conf = GhostsConf.load_from(route.filename)
                key = ghosts_conf.file_ghost_key(route.filename)
                info = GhostInfo(ghost=to_entity_meta(data))
                ghosts_conf.ghosts[key] = info
                ghosts_conf.save(route.filename)
                st.write("saved")

        else:
            st.write(ghost)
        source = inspect.getsource(ghost.__class__)
        if st.toggle("source code", key="ghost_source_code"):
            st.caption(generate_import_path(ghost.__class__))
            st.code(source)
        render_empty()


def render_instruction(conversation: Conversation):
    st.subheader("Instructions")
    instructions = conversation.get_instructions()
    with st.container(border=True):
        st.markdown(instructions)


def render_context_settings(conversation: Conversation):
    st.subheader("Context")
    with st.container(border=True):
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


def render_task_info_settings(task: GoTaskStruct, thread: GoThreadInfo):
    from ghostos.core.runtime.tasks import TaskBrief
    brief = TaskBrief.from_task(task)
    srj.pydantic_instance_form(brief, readonly=True)

    with st.expander(_("Detail"), expanded=False):
        st.write(task.model_dump(exclude_defaults=True))

    st.subheader("Thread Info")
    with st.container(border=True):
        render_thread_messages(thread, max_turn=0)
    render_empty()


def render_thread_messages(thread: GoThreadInfo, max_turn: int = 20):
    turns = list(thread.turns())
    if max_turn > 0:
        turns = turns[-max_turn:]
    debug = get_app_conf().BoolOpts.DEBUG_MODE.get()
    count = 0
    for turn in turns:
        count += render_turn(turn, debug)
    if count == 0:
        st.info("No thread messages yet")
        render_empty()
    render_empty()


def render_event_object(event: Event, debug: bool):
    if event is None:
        return
    from_task_name = event.from_task_name
    if debug and from_task_name is not None:
        st.button(f"from task {from_task_name}", key=f"from task {event.event_id}")
