import streamlit as st

st.title("Applications")

with st.expander("description"):
    st.write("""
hello world
""")

with st.container(border=True):
    st.subheader("Chatbots")
    st.text("chatbots that predefined")
    col1, col2, col3 = st.columns([1,2,3])
    with col1:
        st.button("all", help="show all the AIFuncs or search one", type="primary")
    with col2:
        st.button("WeatherAIFunc", help="show weather AIFuncs")
    with col3:
        st.button("AgenticAIFunc", help="show weather AIFuncs")
