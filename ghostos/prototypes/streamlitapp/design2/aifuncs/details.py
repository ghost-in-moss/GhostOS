import streamlit as st
from streamlit_react_jsonschema import pydantic_form
import inspect
from ghostos.demo.aifuncs.weather import WeatherAIFunc
from ghostos.core.aifunc import get_aifunc_result_type


def show_tab_detail():
    st.subheader("Import Path")
    st.code(f"from {WeatherAIFunc.__module__} import {WeatherAIFunc.__qualname__}", language="python")

    st.subheader("Request Type of the Func")
    instance = pydantic_form(WeatherAIFunc)

    st.subheader("Result Type of the Func")
    result_type = get_aifunc_result_type(WeatherAIFunc)
    instance = pydantic_form(result_type)

    st.subheader("Source Code")
    with st.expander("Full Code", expanded=False):
        mod = inspect.getmodule(WeatherAIFunc)
        codes = inspect.getsource(mod)
        st.code(codes, language="python")

    with st.expander("Request Code", expanded=False):
        codes = inspect.getsource(WeatherAIFunc)
        st.code(codes, language="python")

    with st.expander("Result code", expanded=False):
        result_type = get_aifunc_result_type(WeatherAIFunc)
        codes = inspect.getsource(result_type)
        st.code(codes, language="python")


with st.sidebar:
    st.page_link("aifuncs/index.py", label="AI Function List", icon=":material/list:")

st.title(WeatherAIFunc.__name__)
st.markdown(WeatherAIFunc.__doc__)

tab_detail, tab_run, tab_test, tab_history = st.tabs(["Detail", "Run", "Tests", "History"])

with tab_detail:
    show_tab_detail()

with tab_run:
    st.caption("run")

with tab_test:
    st.caption("test")

with tab_history:
    st.caption("history")
