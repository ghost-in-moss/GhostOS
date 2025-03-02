import streamlit as st
from typing import Iterable, List, NamedTuple, Optional
from ghostos.core.messages import (
    Message, Role, MessageType, FunctionCaller,
    ImageAssetMessage,
)
from ghostos.core.messages.message_classes import ConfirmMessage
from ghostos.core.runtime.events import Event
from ghostos.framework.messages import CompletionUsagePayload, TaskPayload, PromptPayload
from ghostos_common.helpers import gettext as _


class MessageGroup(NamedTuple):
    msg_name: str
    msg_role: str
    stage: str
    messages: List[Message]


def render_messages(messages: Iterable[Message], debug: bool, in_expander: bool, prefix: str = ""):
    groups: List[MessageGroup] = []
    group = MessageGroup("", "", "", [])

    for msg in messages:
        if not msg.is_complete():
            continue
        if msg.name != group.msg_name or msg.role != group.msg_role or msg.stage != group.stage:
            if group.messages:
                groups.append(group)
            group = MessageGroup(msg.name or "", msg.role, msg.stage, [])
        group.messages.append(msg)

    if group.messages:
        groups.append(group)
    for group in groups:
        render_message_group(group, debug, in_expander, prefix)


def render_message_group(group: MessageGroup, debug: bool, in_expander: bool, prefix: str = ""):
    role = group.msg_role
    name = group.msg_name
    stage = group.stage
    caption = f"{role}: {name}" if name else role
    render_role = "user" if role == Role.USER.value else "assistant"
    with st.container():
        if stage:
            with st.expander(stage, expanded=False):
                with st.chat_message(render_role):
                    st.caption(caption)
                    for msg in group.messages:
                        render_message_in_content(msg, debug, prefix=prefix, in_expander=True)
        else:
            with st.container():
                with st.chat_message(render_role):
                    st.caption(caption)
                    for msg in group.messages:
                        render_message_in_content(msg, debug, prefix=prefix, in_expander=in_expander)


def render_message_payloads(message: Message, debug: bool, prefix: str = ""):
    from ghostos.prototypes.streamlitapp.widgets.dialogs import (
        open_task_info_dialog, open_completion_usage_dialog, open_prompt_info_dialog,
        open_message_dialog,
    )

    if not debug:
        st.empty()
        return
    msg_id = message.get_unique_id()
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button(label="Detail", key="Detail" + msg_id):
                open_message_dialog(message)

        with col2:
            task_payload = TaskPayload.read_payload(message)
            if task_payload and st.button(label="Task Info", key="Task Info" + msg_id):
                open_task_info_dialog(task_payload.task_id)

        with col3:
            completion_usage = CompletionUsagePayload.read_payload(message)
            if completion_usage and st.button(label="Token usage", key="token usage" + msg_id):
                open_completion_usage_dialog(completion_usage)

        with col4:
            prompt_payload = PromptPayload.read_payload(message)
            if prompt_payload and st.button(label="Prompt Info", key="Prompt Info" + msg_id):
                open_prompt_info_dialog(prompt_payload.prompt_id)


def render_message_in_content(message: Message, debug: bool, in_expander: bool, *, prefix: str = ""):
    if message.type == MessageType.ERROR.value:
        st.error(f"Message {message.msg_id} Error: {message.content}")

    elif MessageType.is_text(message):
        st.markdown(message.content)

    elif MessageType.FUNCTION_CALL.match(message):
        callers = FunctionCaller.from_message(message)
        render_message_caller(callers, debug, in_expander)

    elif MessageType.FUNCTION_OUTPUT.match(message):
        render_message_caller_output(message, debug, in_expander)
    # todo: more types
    elif MessageType.IMAGE.match(message):
        # render image type message
        render_image_message(message)
    elif MessageType.AUDIO.match(message):
        render_audio_message(message)

    elif MessageType.CONFIRM.match(message):
        # render confirm button
        confirm = ConfirmMessage.from_message(message)
        if confirm and confirm.event:
            event = Event(**confirm.event)
            key = event.event_id
            st.button(confirm.content, key=key, on_click=lambda: save_interactive_event(event), type="primary")

    else:
        st.write(message.model_dump(exclude_defaults=True))
    if message.callers:
        render_message_caller(message.callers, debug, in_expander)

    render_message_payloads(message, debug, prefix)
    st.empty()


def save_interactive_event(event: Event):
    """
    save interactive event to session
    :param event:
    """
    if event:
        st.session_state["interactive_event"] = event


def get_interactive_event() -> Optional[Event]:
    if "interactive_event" in st.session_state:
        event = st.session_state["interactive_event"]
        st.session_state["interactive_event"] = None
        return event
    return None


def render_audio_message(message: Message):
    from ghostos.prototypes.streamlitapp.resources import get_audio_assets
    if message.content:
        st.markdown(message.content)

    assets = get_audio_assets()
    file, data = assets.get_file_and_binary_by_id(message.msg_id)
    if data is not None:
        # st.write(data)
        st.audio(data)


def render_image_message(message: Message):
    from ghostos.prototypes.streamlitapp.resources import get_images_from_image_asset
    if message.type != MessageType.IMAGE.value:
        return
    image_msg = ImageAssetMessage.from_message(message)
    content = image_msg.content
    # render content first
    st.markdown(content)
    image_ids = [image_id.image_id for image_id in image_msg.attrs.images]
    got = get_images_from_image_asset(image_ids)
    for image_info, binary in got.values():
        if binary:
            st.image(binary)
        elif image_info.url:
            st.image(image_info.url)


def render_message_caller_output(message: Message, debug: bool, in_expander: bool):
    if not in_expander:
        with st.expander("Caller Output", expanded=debug):
            st.caption(f"function {message.name or message.call_id} output:")
            st.write(message.content)
    else:
        st.caption(f"function {message.name or message.call_id} output:")
        st.write(message.content)


def render_message_caller(callers: Iterable[FunctionCaller], debug: bool, in_expander: bool):
    if not in_expander:
        with st.expander("Callers", expanded=debug):
            _render_message_caller(callers)
    else:
        _render_message_caller(callers)


def _render_message_caller(callers: Iterable[FunctionCaller]):
    from ghostos.abcd import MossAction
    for caller in callers:
        if caller.name == MossAction.DEFAULT_NAME:
            st.caption(f"function call: {caller.name}")
            code = MossAction.unmarshal_code(caller.arguments)
            st.code(code)
        else:
            st.caption(f"function call: {caller.name}")
            st.write(caller.arguments)


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
