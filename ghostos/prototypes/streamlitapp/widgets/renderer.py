import streamlit as st
import streamlit_react_jsonschema as srj
from pydantic import BaseModel
from ghostos.helpers import generate_import_path, yaml_pretty_dump
from ghostos.streamlit import render_streamlit_object, StreamlitRenderer
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.container import Container
import inspect

__all__ = ['render_object']


def render_object(obj) -> None:
    if obj is None:
        st.info("None")

    container = Singleton.get(Container, st.session_state)
    renderer = container.get(StreamlitRenderer)
    if renderer and renderer.render(obj):
        return

    if render_streamlit_object(obj):
        return

    if inspect.isclass(obj):
        source = inspect.getsource(obj)
        st.subheader(f"Class {generate_import_path(obj)}")
        st.code(source)
    elif inspect.isfunction(obj):
        source = inspect.getsource(obj)
        st.subheader(f"Function {generate_import_path(obj)}")
        st.code(source)
    elif isinstance(obj, BaseModel):
        srj.pydantic_instance_form(obj, readonly=True)
    elif isinstance(obj, dict):
        st.subheader("Dictionary")
        st.markdown(f"""
```yaml
{yaml_pretty_dump(obj)}
```
""")
    elif isinstance(obj, list):
        st.subheader("List")
        st.markdown(f"""
```yaml
{yaml_pretty_dump(obj)}
```
""")
    else:
        type_ = type(obj)
        st.subheader(f"Type {generate_import_path(type_)}")
        with st.container(border=True):
            st.write(obj)
