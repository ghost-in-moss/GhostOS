import streamlit as st
import streamlit_react_jsonschema as srj
from typing import Type
from ghostos.prototypes.streamlitapp.pages.router import ConfigsRoute
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.contracts.configs import Configs, Config
from ghostos.container import Container
from ghostos.helpers import import_from_path
from ghostos.identifier import identify_class


def main():
    route = ConfigsRoute.get(st.session_state)
    classes = []
    classes_identities = []
    for cls_name in route.config_classes:
        cls = import_from_path(cls_name)
        classes.append(cls)
        classes_identities.append(identify_class(cls))

    idx = 0
    for identity in classes_identities:
        cls = classes[idx]
        with st.container(border=True):
            st.subheader(cls.__name__)
            st.markdown(identity.description)
            if st.button("open", key="open_cls_id:" + identity.id):
                open_config_update_dialog(cls)

        idx += 1


@st.dialog("Update Config", width="large")
def open_config_update_dialog(cls: Type[Config]):
    container = Singleton.get(Container, st.session_state)
    configs = container.force_fetch(Configs)
    data = configs.get(cls)
    updated, submitted = srj.pydantic_instance_form(data)
    if submitted and isinstance(updated, Config):
        configs.save(updated)
        st.write("Config saved")
