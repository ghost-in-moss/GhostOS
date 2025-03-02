import streamlit as st
from ghostos.prototypes.streamlitapp.resources import get_app_docs, get_app_conf


def help_document(doc_name: str, label="help"):
    is_helping = get_app_conf().BoolOpts.HELP_MODE.get()
    with st.expander(label=label, expanded=is_helping):
        doc = get_app_docs().read(doc_name)
        st.markdown(doc, unsafe_allow_html=True)


def markdown_document(doc_name: str, **kwargs):
    doc = get_app_docs().read(doc_name)
    if kwargs:
        doc = doc.format(**kwargs)
    st.markdown(doc, unsafe_allow_html=True)
