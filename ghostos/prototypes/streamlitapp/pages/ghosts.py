import streamlit as st
import streamlit_react_jsonschema as srj
import streamlit_paste_button as spb
import time
from PIL.Image import Image
from typing import Iterable, List, Optional
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
from ghostos.prototypes.streamlitapp.resources import (
    get_app_conf, save_uploaded_image, save_pil_image,
)
from ghostos.core.runtime import GoThreadInfo, Event, GoTaskStruct
from ghostos.core.messages import (
    Receiver, Role, ReceiverBuffer, MessageType, Message,
    ImageAssetMessage,
)
from streamlit.logger import get_logger
from ghostos.abcd import Shell, Conversation, Context
from ghostos.identifier import get_identifier
from ghostos.entity import to_entity_meta
from ghostos.helpers import gettext as _
from ghostos.helpers import generate_import_path, yaml_pretty_dump
from ghostos.scripts.cli.utils import GhostsConf, GhostInfo
from streamlit.runtime.uploaded_file_manager import DeletedFile, UploadedFile
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
            thread = conversation.get_thread()
            thread = thread.reset_history([])
            conversation.update_thread(thread)
            st.rerun()

        st.subheader("chat options")
        with st.container(border=True):
            route.realtime = st.toggle(
                _("voice chat"),
                help=_("chat with agent by voice"),
                value=route.realtime
            )
            if route.realtime:
                route.auto_run = False
                route.camera_input = False
                route.image_input = False
            else:
                route.auto_run = st.toggle(
                    _("auto run event"),
                    help=_("automatic run background event"),
                    value=route.auto_run,
                )
                route.camera_input = st.toggle(
                    _("camera_input"),
                    help=_("take picture from camera, the model shall support image type"),
                    value=route.camera_input,
                    key=route.generate_key(st.session_state, "camera_input"),
                )
                route.image_input = st.toggle(
                    "image input",
                    help=_("upload picture, the model shall support image type"),
                    value=route.image_input,
                    key=route.generate_key(st.session_state, "image input"),
                )
            route.bind(st.session_state)

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
        if not route.realtime:
            chatting(route, conversation)
        else:
            realtime(route, conversation)


def realtime(route: GhostChatRoute, conversation: Conversation):
    thread = conversation.get_thread()
    render_thread_messages(thread, max_turn=20)
    debug = get_app_conf().BoolOpts.DEBUG_MODE.get()


def get_conversation(route: GhostChatRoute) -> Conversation:
    conversation = Singleton.get(Conversation, st.session_state, force=False)
    if not conversation or conversation.is_closed():
        shell = Singleton.get(Shell, st.session_state)
        # create conversation
        conversation = shell.sync(route.get_ghost(), route.get_context(), force=True)
        Singleton(conversation, Conversation).bind(st.session_state)
    return conversation


def main_task():
    route = GhostChatRoute.get(st.session_state)
    with st.sidebar:
        # other pages
        with st.container(border=True):
            route.render_page_link(use_container_width=True)
    conversation = get_conversation(route)
    task = conversation.get_task()
    thread = conversation.get_thread()
    st.title("Ghost Task Info")
    render_task_info_settings(task, thread)


def chatting(route: GhostChatRoute, conversation: Conversation):
    if "rerun_chat" not in st.session_state:
        st.session_state["rerun_chat"] = 0
    st.session_state["rerun_chat"] += 1
    for i in range(st.session_state["rerun_chat"]):
        st.empty()
    _chatting(route, conversation)


def _chatting(route: GhostChatRoute, conversation: Conversation):
    chat_input = st.chat_input("message")
    thread = conversation.get_thread()
    render_thread_messages(thread, max_turn=20)
    debug = get_app_conf().BoolOpts.DEBUG_MODE.get()

    pics: List[UploadedFile] = []
    if route.camera_input:
        if pic := st.camera_input(_("Task picture")):
            pics.append(pic)
    else:
        st.empty()

    if route.image_input:
        if pic := st.file_uploader(_("Choose a picture"), type=["png", "jpg", "jpeg"]):
            pics.append(pic)
        paste = spb.paste_image_button(_("Paste a picture"))
        if paste.image_data is not None:
            st.image(paste.image_data, width=300)
            pics.append(paste.image_data)
    else:
        st.empty()

    inputs = st.session_state["ghostos_inputs"] if "ghostos_inputs" in st.session_state else []
    st.session_state["ghostos_inputs"] = []
    if chat_input:
        if pics:
            saved_images = []
            for p in pics:
                if isinstance(p, UploadedFile):
                    image_info = save_uploaded_image(p)
                    saved_images.append(image_info)
                elif isinstance(p, Image):
                    image_info = save_pil_image(p, "user paste image")
                    saved_images.append(image_info)

            message = ImageAssetMessage.from_image_asset(
                name="",
                content=chat_input,
                images=saved_images,
            )
            inputs.append(message)
            st.session_state["ghostos_inputs"] = inputs
            route.new_render_turn(st.session_state)
            st.rerun()
        else:
            inputs.append(Role.USER.new(chat_input))

    if inputs:
        event, receiver = conversation.respond(inputs)
        with st.container():
            render_event(event, debug)
            render_receiver(receiver, debug)

    while not route.media_input() and route.auto_run and conversation.available():
        if event := conversation.pop_event():
            with st.container():
                render_event(event, debug)
                receiver = conversation.respond_event(event)
                render_receiver(receiver, debug)
        else:
            time.sleep(1)


@st.dialog("Textarea")
def video_input_dialog(route: GhostChatRoute):
    text = st.text_area("You message", value="")
    if text:
        st.session_state["chat_text_input"] = text
    logger.debug("end of text area input")


def render_receiver(receiver: Receiver, debug: bool):
    try:
        with receiver:
            with st.container():
                with st.empty():
                    with st.status("thinking"):
                        buffer = ReceiverBuffer.new(receiver.recv())
                    st.empty()
                    if buffer is None:
                        return
                with st.chat_message("assistant"):
                    while buffer is not None:
                        st.logger.get_logger("ghostos").info("receive buffer head: %s", buffer.head())
                        if MessageType.is_text(buffer.head()):
                            with st.empty():
                                contents = chunks_to_st_stream(buffer.chunks())
                                st.write_stream(contents)
                                with st.container():
                                    render_message_in_content(buffer.tail(), debug, in_expander=False)

                        elif MessageType.FUNCTION_CALL.match(buffer.head()):
                            contents = chunks_to_st_stream(buffer.chunks())
                            with st.empty():
                                st.write_stream(contents)
                                with st.container():
                                    render_message_in_content(buffer.tail(), debug, in_expander=False)
                        else:
                            render_message_in_content(buffer.tail(), debug, in_expander=False)
                        # render next item
                        buffer = buffer.next()
    except Exception as e:
        st.error(str(e))
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
    render_thread_messages(thread, max_turn=0)


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
    else:
        st.empty()


def render_event_object(event: Event, debug: bool):
    if event is None:
        return
    from_task_name = event.from_task_name
    if debug and from_task_name is not None:
        st.button(f"from task {from_task_name}", key=f"from task {event.event_id}")
