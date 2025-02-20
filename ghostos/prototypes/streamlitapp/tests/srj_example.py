import streamlit as st
import streamlit_react_jsonschema as srj
from pydantic import BaseModel


class Foo(BaseModel):
    foo: str = "foo"


args, submitted = srj.pydantic_instance_form(Foo(), key="hello")

st.write(submitted)

if value := st.button("hello"):
    st.write(value)
