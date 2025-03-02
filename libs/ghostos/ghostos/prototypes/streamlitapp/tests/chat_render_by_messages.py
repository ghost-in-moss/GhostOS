from typing import List, Any, Dict
import streamlit as st
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

st.session_state.received = []

chart_data = pd.DataFrame(
    {
        "col1": np.random.randn(20),
        "col2": np.random.randn(20),
        "col3": np.random.choice(["A", "B", "C"], 20),
    }
)


class Item(BaseModel):
    method: str = "write"
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)


st.session_state.received.append(Item(
    method="write",
    args=["hello world!"],
))

st.session_state.received.append(Item(
    method="area_chart",
    args=[chart_data],
    kwargs=dict(x="col1", y="col2", color="col3"),
))

messages: List[Item] = st.session_state.received

for item in messages:
    with st.chat_message("assistant"):
        method = getattr(st, item.method)
        method(*item.args, **item.kwargs)


# 可以用数据结构来定义, 但并不优雅.
# 更好的办法是, 数据保存在文件, 同时定义一个函数. 函数接受回调.
# like:


class RenderObject(BaseModel):
    data_path: str = Field(description="the path to save the data")
    data_type: str = Field(description="the data type that follow with a callback func to render the data")
