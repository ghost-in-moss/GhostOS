from typing import TypeVar, Tuple
import streamlit as st
import streamlit_react_jsonschema as srj
from pydantic import BaseModel
from ghostos_common.helpers import generate_import_path, yaml_pretty_dump
from ghostos.streamlit import render_streamlit_object, StreamlitRenderer
from ghostos.core.runtime import (
    TaskBrief, GoTasks, GoTaskStruct,
    GoThreads, GoThreadInfo, Turn,
    Event, EventTypes,
)
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos_container import Container
from ghostos_common.helpers import gettext as _
import inspect

__all__ = [
    'render_object',
    'render_task', 'render_task_by_id',
    'render_thread', 'render_event', 'render_turn', 'render_event_object',
    'render_empty',

    'render_turn_delete',
]

T = TypeVar('T')


def render_task_by_id(task_id: str):
    container = Singleton.get(Container, st.session_state)
    tasks = container.force_fetch(GoTasks)
    task = tasks.get_task(task_id)
    if task is None:
        st.info(f"Task {task_id} not found")
        st.empty()
        return
    render_task(task)


def render_empty():
    for i in range(20):
        st.empty()


def render_task(task: GoTaskStruct):
    brief = TaskBrief.from_task(task)
    srj.pydantic_instance_form(brief, readonly=True)

    with st.expander(_("Detail"), expanded=False):
        st.write(task.model_dump(exclude_defaults=True))

    if task.children:
        st.subheader("Subtasks")
        st.write("todo")

    container = Singleton.get(Container, st.session_state)
    threads = container.force_fetch(GoThreads)
    thread = threads.get_thread(task.thread_id)
    st.subheader("Thread Info")
    if thread is None:
        st.info(f"Thread {task.thread_id} is not created yet")
        st.empty()
        return
    with st.container(border=True):
        render_thread(thread, prefix="render_thread_in_task", debug=False)


def render_thread(thread: GoThreadInfo, max_turn: int = 20, prefix: str = "", debug: bool = False):
    st.subheader("Thread Info")
    turns = list(thread.turns(truncate=True))
    turns = turns[-max_turn:]
    count = 0
    for turn in turns:
        count += render_turn(turn, debug, prefix)
        render_turn_delete(thread, turn, debug)

    if count == 0:
        st.info("No thread messages yet")


def render_turn_delete(thread: GoThreadInfo, turn: Turn, debug: bool):
    if debug:
        st.divider()
        if st.button("delete turn", key=f"{thread.id}--{turn.turn_id}"):
            thread.delete_turn(turn.turn_id)
            save_thread(thread)


def save_thread(thread: GoThreadInfo):
    from ghostos.prototypes.streamlitapp.resources import get_container
    from ghostos.core.runtime.threads import GoThreads
    container = get_container()
    threads = container.force_fetch(GoThreads)
    threads.save_thread(thread)
    st.rerun()


def render_turn(turn: Turn, debug: bool, prefix: str = "") -> int:
    from ghostos.prototypes.streamlitapp.widgets.messages import render_messages
    if turn.summary is not None:
        st.info("summary:\n" + turn.summary)

    if not turn.approved:
        with st.expander(_("unapproved"), expanded=True):
            messages = list(turn.messages(False))
            render_messages(messages, debug, in_expander=True, prefix=prefix)

    elif turn.is_from_client() or turn.is_from_self():
        messages = list(turn.messages(False))
        render_messages(messages, debug, in_expander=False, prefix=prefix)
    # from other task
    else:
        event = turn.event
        if event is not None:
            sub_title = _("on event: ") + event.type
            with st.expander(sub_title, expanded=False):
                event_messages = turn.event_messages()
                render_messages(event_messages, debug, in_expander=True)
                render_event_object(event, debug)
        if turn.added:
            render_messages(turn.added, debug, in_expander=False)
        messages = list(turn.messages(False))

    return len(messages)


def render_event(event: Event, debug: bool):
    from ghostos.prototypes.streamlitapp.widgets.messages import render_messages
    if event is None:
        return
    if event.callback:
        sub_title = _("background event: ") + event.type
        with st.expander(sub_title, expanded=False):
            messages = event.iter_message(show_instruction=True)
            render_messages(messages, debug, in_expander=True)
    else:
        messages = event.iter_message(show_instruction=True)
        with st.container():
            render_messages(messages, debug, in_expander=False)


def render_event_object(event: Event, debug: bool):
    if event is None:
        return
    from_task_name = event.from_task_name
    if debug and from_task_name is not None:
        st.button(f"from task {from_task_name}", key=f"from task {event.event_id}")


def render_object(obj: T, immutable: bool = False) -> Tuple[T, bool]:
    """
    render an object in a streamlit compatible way.
    :param obj: the object to render
    :param immutable: is the object immutable?
    :return: [value: obj after rendering, changed: is object changed]
    """
    if obj is None:
        st.info("None")

    container = Singleton.get(Container, st.session_state)
    renderer = container.get(StreamlitRenderer)
    if renderer:
        r = renderer.render(obj)
        if r is not None:
            return r.value, r.changed

    if r := render_streamlit_object(obj):
        return r.value, r.changed

    if inspect.isclass(obj):
        source = inspect.getsource(obj)
        st.subheader(f"Class {generate_import_path(obj)}")
        st.code(source)
        return obj, False
    elif inspect.isfunction(obj):
        source = inspect.getsource(obj)
        st.subheader(f"Function {generate_import_path(obj)}")
        st.code(source)
        return obj, False
    elif isinstance(obj, BaseModel):
        obj, submitted = srj.pydantic_instance_form(obj, readonly=immutable)
        return obj, submitted
    elif isinstance(obj, dict):
        st.subheader("Dictionary")
        st.markdown(f"""
```yaml
{yaml_pretty_dump(obj)}
```
""")
        return obj, False
    elif isinstance(obj, list):
        st.subheader("List")
        st.markdown(f"""
```yaml
{yaml_pretty_dump(obj)}
```
""")
        return obj, False
    else:
        type_ = type(obj)
        st.subheader(f"Type {generate_import_path(type_)}")
        with st.container(border=True):
            st.write(obj)
            return obj, False
