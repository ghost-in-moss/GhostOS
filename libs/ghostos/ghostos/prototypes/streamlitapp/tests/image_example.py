import streamlit as st

if pic := st.camera_input("You photo"):
    st.write(pic)
    data = pic.getvalue()
    with open("pic.jpg", "wb") as f:
        f.write(data)
        st.write("write to file")
