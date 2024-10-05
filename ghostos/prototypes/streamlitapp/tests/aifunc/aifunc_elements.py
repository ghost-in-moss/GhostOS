import streamlit as st
from ghostos.prototypes.streamlitapp.patches import streamlit_pydantic as sp
import inspect

from ghostos.core.aifunc import get_aifunc_result_type
from ghostos.app.src.aifuncs.weather import WeatherAIFunc, WeatherAIFuncResult

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
sp.pydantic_output(request)

# aifunc result pydantic output
result = WeatherAIFuncResult()
st.title("AiFuncs Result output")
sp.pydantic_output(result.model_copy())

# input form
st.title("Aifunc Input Form")
if input_data := sp.pydantic_input(
        "weather_input",
        model=WeatherAIFunc,
):
    st.json(input_data)

st.title("Aifunc Input Submit Form")
with st.form(key="aifunc_form"):
    data = sp.pydantic_input(key="my_custom_form_model", model=WeatherAIFunc)
    submitted = st.form_submit_button(label="Submit")
    st.write(f"submitted: {submitted}")
    st.json(data)

st.title("Aifunc Input Submit With Button")
data = sp.pydantic_input(key="aifunc model", model=WeatherAIFunc)
if st.button("run the func"):
    obj = WeatherAIFunc(**data)
    st.json(obj.model_dump())
