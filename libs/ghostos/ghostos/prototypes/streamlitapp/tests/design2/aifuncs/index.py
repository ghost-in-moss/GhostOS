import streamlit as st

AIFUNC_SEARCH_MESSAGES = "aifunc.index.messages"

with st.sidebar:
    if search_aifunc := st.text_input(
        "Search AIFUNC",
        placeholder="description of the AIFunc you want",
    ):
        st.write(search_aifunc)

st.title("AI Functions")

with st.expander("introduction"):
    st.write("hello world")

pressed = False
for i in range(5):
    with st.container(border=True):
        st.subheader("AIFuncName")
        st.caption("from foo.bar.zoo import xxx")
        st.text("description of the AIFunc __doc__")
        hit = st.button("enter", key=f"button-{i}")
        if not pressed and hit:
            pressed = True

if pressed:
    st.switch_page("aifuncs/details.py")
