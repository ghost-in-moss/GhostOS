import streamlit as st
import streamlit_react_jsonschema as srj
import streamlit_paste_button as spb
import time
from PIL.Image import Image
from typing import Iterable, List, Optional
from ghostos.prototypes.streamlitapp.pages.router import (
    GhostChatRoute, GhostTaskRoute, ShowThreadRoute
)
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.prototypes.streamlitapp.widgets.messages import (
    render_message_in_content, render_messages, get_interactive_event,
)
from ghostos.prototypes.streamlitapp.widgets.renderer import (
    render_object, render_event, render_turn, render_turn_delete,
    render_empty,
)
from ghostos.prototypes.streamlitapp.resources import (
    get_app_conf, save_uploaded_image, save_pil_image,
    get_container,
)

from ghostos.core.runtime import GoThreadInfo, Event, GoTaskStruct
from ghostos.core.messages import (
    Receiver, Role, ReceiverBuffer, MessageType, Message,
    ImageAssetMessage,
)
from streamlit.logger import get_logger
from ghostos.abcd.realtime import OperatorName, RealtimeApp
from ghostos.abcd import Matrix, Conversation, Context
from ghostos_common.identifier import get_identifier
from ghostos_common.entity import to_entity_meta
from ghostos_common.helpers import generate_import_path, yaml_pretty_dump, uuid, gettext as _
from ghostos.core.runtime import GoTasks
from ghostos.scripts.cli.utils import DirGhostsConf, GhostInfo
from streamlit.runtime.uploaded_file_manager import UploadedFile
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
    if not conversation or not conversation.refresh():
        st.error("Conversation is Closed")
        return
    # run the pages
    realtime_app = Singleton.get(RealtimeApp, st.session_state, force=False)
    with st.sidebar:
        # other pages
        if st.button("Task Info", use_container_width=True):
            _route = GhostTaskRoute(task_id=conversation.get_task().task_id)
            _route.switch_page()
            return
        if st.button("Thread Info", use_container_width=True):
            task = conversation.get_task()
            ShowThreadRoute(thread_id=task.thread_id, task_id=task.task_id).switch_page()
            return
        if st.button("Reset Task", use_container_width=True):
            shell = Singleton.get(Matrix, st.session_state, force=True)
            task = shell.get_or_create_task(conversation.get_ghost(), always_create=True, save=False)
            task.thread_id = uuid()
            shell.tasks().save_task(task)
            route.switch_page()
            return

        if st.button("New Thread", use_container_width=True):
            thread = conversation.get_thread()
            fork = thread.fork()
            thread = fork.reset_history([])
            conversation.update_thread(thread)
            route.switch_page()
            return
        if st.button("Clear Thread Messages", use_container_width=True):
            thread = conversation.get_thread()
            thread = thread.reset_history([])
            conversation.update_thread(thread)
            route.switch_page()
            return

        st.subheader("page options")
        with st.container(border=True):
            show_ghost_settings = st.toggle("ghost settings")
            show_instruction = st.toggle("show instructions")
            show_state_values = st.toggle("show state values")
            show_context = st.toggle("show context")

        st.subheader("chat options")
        with st.container(border=True):
            route.realtime = st.toggle(
                _("realtime chat"),
                help=_("chat with agent by voice"),
                value=route.realtime
            )
            if route.realtime:
                route.auto_run = False
                route.camera_input = False
                route.image_input = False
                created = False
                with st.container():
                    route.vad_mode = st.toggle(
                        _("vad mod"),
                        help=_("the realtime api auto detected your input"),
                        value=route.vad_mode,
                    )
                    route.listen_mode = st.toggle(
                        _("listening"),
                        help=_("turn on or turn off listening"),
                        value=route.listen_mode,
                    )

                    if realtime_app is None:
                        realtime_app = get_realtime_app(conversation)
                        created = True
                    elif realtime_app.conversation is not conversation:
                        realtime_app.close()
                        realtime_app = get_realtime_app(conversation)
                        created = True
                    # error about realtime.
                    if realtime_app is None:
                        st.error(
                            "Realtime mode need pyaudio installed successfully. "
                            "run `pip install 'ghostos[realtime]'` first"
                        )
                        route.realtime = False
                    else:
                        Singleton(realtime_app, RealtimeApp).bind(st.session_state)
                        if created:
                            realtime_app.start(vad_mode=route.vad_mode, listen_mode=route.listen_mode)
                        else:
                            realtime_app.set_mode(vad_mode=route.vad_mode, listen_mode=route.listen_mode)

                        canceled = get_response_button_count()
                        if not route.vad_mode:
                            if st.button("response", key=f"create_realtime_response_{canceled}"):
                                incr_response_button_count()
                                realtime_app.operate(OperatorName.respond.new(""))
                                st.rerun()
                        if st.button("cancel response", key=f"cancel_realtime_response_{canceled}"):
                            incr_response_button_count()
                            realtime_app.operate(OperatorName.cancel_responding.new(""))
                            st.rerun()

            else:
                if realtime_app is not None:
                    # if bind realtime app, release it.
                    realtime_app.close()
                    Singleton.release(RealtimeApp, st.session_state)

                with st.container():
                    route.auto_run = st.toggle(
                        _("auto run event"),
                        help=_("automatic run background event"),
                        value=route.auto_run,
                    )
                    route.camera_input = st.toggle(
                        _("camera"),
                        help=_("take picture from camera, the model shall support image type"),
                        value=route.camera_input,
                        key=route.generate_key(st.session_state, "camera_input"),
                    )
                    route.image_input = st.toggle(
                        "upload image",
                        help=_("upload picture, the model shall support image type"),
                        value=route.image_input,
                        key=route.generate_key(st.session_state, "image input"),
                    )
            route.bind(st.session_state)

    # header
    st.title("Ghost")
    with st.container(border=True):
        ghost = conversation.get_ghost()
        id_ = get_identifier(ghost)
        import_path = generate_import_path(ghost.__class__)
        data = {
            _("name"): id_.name,
            _("desc"): id_.description,
            _("class"): import_path,
            _("task id"): conversation.task_id,
            _("thread id"): conversation.get_thread().id,
        }
        if route.filename:
            data[_("from")] = route.filename
        # description
        st.markdown(f"""
```yaml
{yaml_pretty_dump(data)}
```
""")

    # render ghost settings
    if show_ghost_settings:
        render_ghost_settings(conversation, route)
    if show_instruction:
        render_instruction(conversation)
    if show_state_values:
        render_state_values(conversation)
    if show_context:
        render_context_settings(conversation)

    # inputs
    if not route.realtime:
        st.subheader("Chat")
        chatting(route, conversation)
    else:
        st.subheader("Realtime Chat")
        run_realtime(route, realtime_app)


def run_realtime(route: GhostChatRoute, app: RealtimeApp):
    if app is None:
        st.error("Realtime mode is not installed ready yet.")
    try:
        _run_realtime(route, app)
    except Exception as e:
        app.close()
        raise e


def get_response_button_count() -> int:
    if "real_time_canceled" not in st.session_state:
        st.session_state["real_time_canceled"] = 0
    return st.session_state["real_time_canceled"]


def incr_response_button_count():
    if "real_time_canceled" not in st.session_state:
        st.session_state["real_time_canceled"] = 0
    st.session_state["real_time_canceled"] += 1


def _run_realtime(route: GhostChatRoute, app: RealtimeApp):
    thread = app.conversation.get_thread()
    render_thread_messages(thread)
    messages = app.history_messages()
    render_messages(messages, debug=False, in_expander=False)
    while not app.is_closed():
        state = "waiting"
        buffer = None
        with st.empty():
            with st.status(state) as status:
                while buffer is None:
                    state, operators = app.state()
                    status.update(label=state)
                    buffer = app.output()
                    if buffer is None:
                        time.sleep(0.5)
                        continue

            while buffer is not None:
                head = buffer.head()
                role = head.role
                role = "user" if role == Role.USER.value else "assistant"
                with st.chat_message(role):
                    with st.empty():
                        with st.container():
                            chunks = chunks_to_st_stream(buffer.chunks())
                            st.write_stream(chunks)
                        with st.container():
                            render_message_in_content(buffer.tail(), False, False)
                    buffer = buffer.next()
    st.write("app is close")


def get_realtime_app(conversation: Conversation) -> Optional[RealtimeApp]:
    # 获取并检查 realtime extras 的所有依赖是否已安装
    from importlib.metadata import distribution
    dist = distribution('ghostos')
    requires = dist.requires or []
    realtime_requires = [r for r in requires if 'extra == "realtime"' in r]
    # 如果所有依赖都已安装，importlib.metadata 就能找到它们
    for pkg in realtime_requires:
        # 从依赖字符串中提取包名（去掉版本和其他限制条件）
        pkg_name = pkg.split()[0]
        try:
            distribution(pkg_name)
        except ModuleNotFoundError as e:
            logger.exception(e)
            return None

    from ghostos.framework.audio import get_pyaudio_pcm16_speaker, get_pyaudio_pcm16_listener
    from ghostos.framework.openai_realtime import get_openai_realtime_app
    app_conf = get_app_conf()
    audio_input = app_conf.audio_input
    audio_output = app_conf.audio_output
    speaker = get_pyaudio_pcm16_speaker(
        input_rate=audio_output.input_rate,
        output_rate=audio_output.output_rate,
        buffer_size=audio_output.buffer_size,
        channels=audio_output.channels,
        output_device_index=audio_output.output_device_index,
    )
    listener = get_pyaudio_pcm16_listener(
        rate=audio_input.sample_rate,
        output_rate=audio_input.output_rate,
        interval=audio_input.interval,
        channels=audio_input.channels,
        chunk_size=audio_input.chunk_size,
        input_device_index=audio_input.input_device_index,
    )
    vad_mode = True
    return get_openai_realtime_app(conversation, vad_mode=vad_mode, listener=listener, speaker=speaker)


def get_conversation(route: GhostChatRoute) -> Optional[Conversation]:
    conversation = Singleton.get(Conversation, st.session_state, force=False)
    if not conversation or conversation.is_closed():
        shell = Singleton.get(Matrix, st.session_state)
        # create conversation
        try:
            conversation = shell.sync_task(route.task_id, force=True)
        except Exception as e:
            logger.exception(e)
            st.error(e)
            return None
        if conversation:
            Singleton(conversation, Conversation).bind(st.session_state)
    return conversation


def main_task():
    route = GhostTaskRoute().get_or_bind(st.session_state)
    with st.sidebar:
        if st.button("Chat", use_container_width=True):
            GhostChatRoute(task_id=route.task_id).switch_page()

    st.title("Ghost Task Info")
    tasks = get_container().force_fetch(GoTasks)
    task = tasks.get_task(route.task_id)
    if task is None:
        st.error("Task not found")
        return
    render_task_info_settings(task)


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
    render_thread_messages(thread, max_turn=20, truncate=True)
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
    else:
        event = get_interactive_event()
        if event is not None:
            receiver = conversation.respond_event(event, streaming=True)
            with st.container():
                render_event(event, debug)
                render_receiver(receiver, debug)
            st.rerun()

    interval = 0.1
    while not route.media_input() and route.auto_run and conversation.available():
        if event := conversation.pop_event():
            with st.container():
                render_event(event, debug)
                receiver = conversation.respond_event(event)
                render_receiver(receiver, debug)
                interval = 0.1
        else:
            time.sleep(interval)
            interval = 1


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
                    render_receive_buffer(buffer, debug)

    except Exception as e:
        st.error(str(e))
        st.exception(e)


def render_receive_buffer(buffer: ReceiverBuffer, debug: bool):
    """
    iterate buffer and render each one
    :param buffer:
    :param debug:
    :return:
    """
    stage = ""
    while buffer is not None:
        st.logger.get_logger("ghostos").debug("receive buffer head: %s", buffer.head())
        head = buffer.head()
        if head.stage != stage:
            stage = head.stage
            stage_name = stage or "output"
            with st.status(stage_name):
                pass
        _render_single_buffer(buffer, head, debug, False)
        # render next item
        buffer = buffer.next()


def _render_single_buffer(buffer: ReceiverBuffer, head: Message, debug: bool, in_expander: bool):
    if head.name:
        msg_caption = f"{head.role}: {head.name}"
        st.caption(msg_caption)

    if MessageType.is_text(head):
        with st.empty():
            contents = chunks_to_st_stream(buffer.chunks())
            st.write_stream(contents)
            with st.container():
                render_message_in_content(buffer.tail(), debug, in_expander=in_expander)

    elif MessageType.FUNCTION_CALL.match(buffer.head()):
        contents = chunks_to_st_stream(buffer.chunks())
        with st.empty():
            st.write_stream(contents)
            with st.container():
                render_message_in_content(buffer.tail(), debug, in_expander=True)
    else:
        with st.container():
            render_message_in_content(buffer.tail(), debug, in_expander=in_expander)


def chunks_to_st_stream(chunks: Iterable[Message]) -> Iterable[str]:
    for chunk in chunks:
        if chunk.content:
            yield chunk.content


def render_ghost_settings(conversation: Conversation, route: GhostChatRoute):
    st.subheader(_("Settings"))
    with st.container(border=True):
        if route is None:
            st.error("page is not configured")
            return
        ghost = conversation.get_ghost()
        # render ghost info
        if isinstance(ghost, BaseModel):
            data, submitted = srj.pydantic_instance_form(ghost)
            if route.filename and submitted:
                ghosts_conf = DirGhostsConf.load_from(route.filename)
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
    instruction = conversation.get_system_instruction()
    with st.container(border=True):
        st.markdown(instruction)


def render_state_values(conversation: Conversation):
    values = conversation.get_state_values()
    with st.container(border=True):
        for key, value in values.items():
            st.subheader(key)
            st.write(value)


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


def render_task_info_settings(task: GoTaskStruct):
    from ghostos.core.runtime.tasks import TaskBrief
    brief = TaskBrief.from_task(task)
    srj.pydantic_instance_form(brief, readonly=True)

    with st.expander(_("Detail"), expanded=False):
        st.write(task.model_dump(exclude_defaults=True))


def render_thread_messages(thread: GoThreadInfo, max_turn: int = 20, truncate: bool = True):
    turns = list(thread.turns(truncate=truncate))
    if max_turn > 0:
        turns = turns[-max_turn:]
    debug = get_app_conf().BoolOpts.DEBUG_MODE.get()
    count = 0
    for turn in turns:
        count += render_turn(turn, debug)
        if count > 1:
            render_turn_delete(thread, turn, debug)
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
