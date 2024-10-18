import streamlit as st
from ghostos.container import Container
from ghostos.contracts.translation import Translation
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.prototypes.streamlitapp.configs import AppConf


@st.cache_resource
def container() -> Container:
    return Singleton.get(Container, st.session_state)


@st.cache_resource
def translator():
    conf = AppConf.get_or_bind(st.session_state)
    translation = container().force_fetch(Translation)
    return translation.get_domain(conf.name).get_translator(conf.default_lang)


def trans(text: str, **kwargs) -> str:
    """
    i18n trans
    """
    return translator().gettext(text, **kwargs)
