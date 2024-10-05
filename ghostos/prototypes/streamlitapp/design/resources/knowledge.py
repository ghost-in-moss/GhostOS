import streamlit as st

st.write(st.query_params.to_dict())

with st.chat_message("assistant"):
    st.write("hello world!")
