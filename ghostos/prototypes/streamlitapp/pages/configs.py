import inspect

import streamlit as st
import streamlit_react_jsonschema as srj
from typing import Type
from ghostos.prototypes.streamlitapp.pages.router import ConfigsRoute
from ghostos.prototypes.streamlitapp.resources import get_container
from ghostos.contracts.configs import Configs, Config
from ghostos.contracts.workspace import Workspace
from ghostos_common.helpers import import_from_path
from ghostos_common.identifier import identify_class
from os.path import join


def main():
    route = ConfigsRoute.get(st.session_state)
    classes = []
    container = get_container()
    ws = container.force_fetch(Workspace)
    configs_dir = ws.configs().abspath()

    for cls_name in route.config_classes:
        cls = import_from_path(cls_name)
        classes.append(cls)
        identity = identify_class(cls)
        filename = ""
        if issubclass(cls, Config):
            filename = join(configs_dir, cls.conf_path())

        with st.container(border=True):
            st.subheader(cls.__name__)
            st.caption(identity.description)
            if filename:
                st.caption(f"at: `{filename}`\n")
            st.caption(f"class: `{identity.id}`")
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                open_form = st.toggle("edit", key="open_cls_form:" + identity.id)
            with col2:
                show_source = st.toggle("code", key="show_source:" + identity.id)

            if open_form:
                open_config_update_dialog(cls)
            if show_source:
                code = inspect.getsource(cls)
                st.code(code)


def open_config_update_dialog(cls: Type[Config]):
    container = get_container()
    configs = container.force_fetch(Configs)
    data = configs.get(cls)
    updated, submitted = srj.pydantic_instance_form(data)
    if submitted and isinstance(updated, Config):
        configs.save(updated)
        st.write("Config saved")
