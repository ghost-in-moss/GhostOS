import streamlit as st
import streamlit_react_jsonschema as srj
import inspect

from ghostos.core.aifunc import get_aifunc_result_type
from ghostos.demo.aifuncs.weather import WeatherAIFunc, WeatherAIFuncResult

# source code
st.title("Source Code")
filepath = inspect.getmodule(WeatherAIFunc).__file__
with open(filepath, "r") as f:
    code = f.read()
    st.code(code, language="python", line_numbers=True)

# AiFunc code
aifunc_code = inspect.getsource(WeatherAIFunc)
st.title("AiFunc code")
st.code(aifunc_code, language="python", line_numbers=True)

# AiFunc result type Code
aifunc_result_type = get_aifunc_result_type(WeatherAIFunc)
aifunc_result_code = inspect.getsource(aifunc_result_type)
st.title("AiFunc result code")
st.code(aifunc_result_code, language="python", line_numbers=True)

# json schema
st.title("AiFuncs JSON Schema")
st.json(WeatherAIFunc.model_json_schema())

# aifunc pydantic output
request = WeatherAIFunc()
st.title("AiFunc output")
srj.pydantic_instance_form(request)

# aifunc result pydantic output
st.title("AiFuncs Result output")
srj.jsonschema_form("test", schema=WeatherAIFuncResult.model_json_schema(), default={})
