import streamlit as st
from ghostos_common.helpers import gettext as _, yaml_pretty_dump
from ghostos.core.messages import CompletionUsagePayload
from ghostos.core.messages import Message
from ghostos.prototypes.streamlitapp.widgets.renderer import render_empty


@st.dialog(title=_("Code"), width="large")
def open_code_dialog(title: str, code: str):
    st.subheader(title)
    st.code(code, line_numbers=True, wrap_lines=True)
    render_empty()


@st.dialog(title=_("Task Info"), width="large")
def open_task_info_dialog(task_id: str):
    from ghostos.prototypes.streamlitapp.widgets.renderer import render_task_by_id
    render_task_by_id(task_id)
    render_empty()


@st.dialog(title=_("Token Usage"), width="large")
def open_completion_usage_dialog(completion: CompletionUsagePayload):
    import streamlit_react_jsonschema as srj
    srj.pydantic_instance_form(completion, readonly=True)
    render_empty()


@st.dialog(title=_("Message Detail"), width="large")
def open_message_dialog(message: Message):
    st.json(message.model_dump_json(indent=2))


@st.dialog(title=_("Prompt Info"), width="large")
def open_prompt_info_dialog(prompt_id: str):
    import streamlit_react_jsonschema as srj
    from ghostos.prototypes.streamlitapp.utils.session import Singleton
    from ghostos.prototypes.streamlitapp.widgets.messages import render_messages
    from ghostos_container import Container
    from ghostos.core.llms import PromptStorage

    prefix = "prompt-info"
    container = Singleton.get(Container, st.session_state)
    storage = container.get(PromptStorage)
    if storage is None:
        st.error(f"Prompt storage is not initialized")
        return
    prompt = storage.get(prompt_id)
    if prompt is None:
        st.error(f"Prompt {prompt_id} not found")
        return

    # description
    desc = prompt.model_dump(include={"id", "description", "run_start", "first_token", "run_end"})
    st.markdown(f"""
```yaml
{yaml_pretty_dump(desc)}
```
""")

    # model info
    if prompt.model:
        st.subheader("Model Info")
        srj.pydantic_instance_form(prompt.model, readonly=True)

    # prompt error
    if prompt.error:
        st.subheader("Prompt error")
        st.error(prompt.error)

    # prompt functions
    if prompt.functions:
        st.subheader(_("Functions"))
        with st.container(border=True):
            for func in prompt.functions:
                with st.expander(func.name):
                    st.write(func.model_dump())
    if prompt.functional_tokens:
        st.subheader("Functional Tokens")
        with st.container(border=True):
            for ft in prompt.functional_tokens:
                with st.expander(ft.name):
                    st.write(ft.model_dump())

    system_prompt = prompt.system_prompt()
    st.subheader("System Prompt")
    with st.container(border=True):
        st.markdown(system_prompt)

    if prompt.history:
        st.subheader(_("History"))
        with st.container(border=True):
            render_messages(prompt.history, False, False, prefix=prefix)
    if prompt.inputs:
        st.subheader(_("Input"))
        with st.container(border=True):
            render_messages(prompt.inputs, False, False, prefix)
    if prompt.added:
        st.subheader(_("Added"))
        with st.container(border=True):
            render_messages(prompt.added, False, False, prefix)

    if prompt.request_params:
        with st.expander("Request Parameters", expanded=False):
            st.write(prompt.request_params)

    render_empty()
