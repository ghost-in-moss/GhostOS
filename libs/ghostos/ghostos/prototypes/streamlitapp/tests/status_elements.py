import streamlit as st

st.success('This is a success message!', icon="✅")
st.info('This is a purely informational message', icon="ℹ️")
st.warning('This is a warning', icon="⚠️")
st.error('This is an error', icon="🚨")
e = RuntimeError("This is an exception of type RuntimeError")
st.exception(e)
