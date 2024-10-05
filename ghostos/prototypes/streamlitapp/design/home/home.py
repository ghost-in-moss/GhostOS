import streamlit as st

from os.path import join, dirname
from ghostos import demo

readme_file = join(dirname(dirname(dirname(demo.__file__))), "README.md")

with open(readme_file, 'r') as f:
    content = f.read()
    st.markdown(content, unsafe_allow_html=True)
