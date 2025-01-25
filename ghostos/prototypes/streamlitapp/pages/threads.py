import streamlit as st
from ghostos.helpers import yaml_pretty_dump
from ghostos.prototypes.streamlitapp.pages.router import ShowThreadRoute
from ghostos.prototypes.streamlitapp.resources import get_container, get_app_conf
from ghostos.prototypes.streamlitapp.widgets.renderer import render_thread
from ghostos.core.runtime.threads import GoThreads, GoThreadInfo, thread_to_markdown
import os
import yaml


def show_thread():
    st.title("Show Thread Info")
    route = ShowThreadRoute().get_or_bind(st.session_state)

    thread_id = route.thread_id
    if not thread_id:
        st.error("No thread specified")
        return
    container = get_container()
    threads = container.force_fetch(GoThreads)

    thread = threads.get_thread(thread_id, create=False)
    if not thread:
        filename = os.path.abspath(thread_id)
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                content = f.read()
                data = yaml.safe_load(content)
                thread = GoThreadInfo(**data)

    if not thread:
        st.error(f"Thread {thread_id} does not exist")
        return

    with st.sidebar:
        if filename := st.text_input("output markdown filename (without `.md`)"):
            try:
                saved_at = save_thread_markdown_file(thread, filename)
                st.info(f"save thread as markdown file: {saved_at}")
            except Exception as e:
                st.error(e)

    desc = thread.model_dump(include={"id", "parent_id", "root_id", "extra"})
    st.markdown(f"""
```yaml
{yaml_pretty_dump(desc)}
```
""")
    is_debug = get_app_conf().BoolOpts.DEBUG_MODE.get()
    render_thread(thread, debug=is_debug)


def save_thread_markdown_file(thread: GoThreadInfo, filename: str) -> str:
    if not filename.endswith(".md"):
        filename = filename + ".md"

    filename = os.path.abspath(filename)
    content = thread_to_markdown(thread)
    with open(filename, "w") as f:
        f.write(content)
    open_dialog_markdown_content(content)
    return filename


@st.dialog("Thread Markdown Output", width="large")
def open_dialog_markdown_content(content: str):
    st.markdown(content, unsafe_allow_html=False)
