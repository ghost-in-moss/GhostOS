import streamlit as st

st.title("Chat")
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "hello world"}]
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
if prompt := st.chat_input("say something"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = f"Echo: {prompt}"
    with st.chat_message("assistant"):
        st.write_stream([c for c in response])
    st.session_state.messages.append({"role": "assistant", "content": response})

