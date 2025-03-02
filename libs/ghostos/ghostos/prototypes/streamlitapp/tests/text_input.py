import streamlit as st


@st.fragment
def show_text_input():
    text_input = st.session_state['text_input']
    with st.empty():
        st.write(text_input)


title = st.text_input(
    "Movie title",
    "Life of Brian",
    key="text_input",
)

show_text_input()

st.write("The current movie title is", title)
