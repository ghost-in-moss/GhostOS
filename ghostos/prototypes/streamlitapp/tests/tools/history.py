import streamlit as st

x = st.slider("Select a value")
st.write(x, "squared is", x * x)
values = {k: v for k, v in st.query_params.conversation_item_states()}
st.write(values)
