from typing import TypeVar, Tuple
import streamlit as st
import streamlit_react_jsonschema as srj
from pydantic import BaseModel
from ghostos.helpers import generate_import_path, yaml_pretty_dump
from ghostos.streamlit import render_streamlit_object, StreamlitRenderer
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.container import Container
import inspect

__all__ = ['render_object']

T = TypeVar('T')


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
