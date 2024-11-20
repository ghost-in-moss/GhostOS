from typing import Optional, Dict

from enum import Enum
from pydantic import Field
import streamlit as st
from ghostos.container import Container
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.contracts.configs import YamlConfig, Configs
from ghostos.contracts.documents import DocumentRegistry, Documents
from ghostos.helpers import GHOSTOS_DOMAIN


@st.cache_resource
def get_container() -> Container:
    return Singleton.get(Container, st.session_state)


class AppConf(YamlConfig):
    relative_path = "streamlit_app.yml"

    domain: str = GHOSTOS_DOMAIN
    lang: str = Field("zh", description="lang of the app")

    bool_options: Dict[str, bool] = Field(
        default_factory=dict,
    )

    class BoolOpts(str, Enum):
        HELP_MODE = "ghostos.streamlit.app.help_mode"
        """global help mode"""

        DEBUG_MODE = "ghostos.streamlit.app.debug_mode"

        def get(self) -> bool:
            return get_app_conf().bool_options.get(self.name, True)

        def render_toggle(
                self,
                label: str, *,
                tips: Optional[str] = None,
                disabled: bool = False,
        ) -> None:
            key = self.value
            val = self.get()

            def on_change():
                """
                change the config
                """
                value = st.session_state[key]
                conf = get_app_conf()
                conf.bool_options[self.name] = value
                configs = get_container().force_fetch(Configs)
                configs.save(conf)

            st.toggle(
                label,
                key=self.value,
                value=val,
                disabled=disabled,
                help=tips,
                on_change=on_change,
            )


@st.cache_resource
def get_app_conf() -> AppConf:
    from ghostos.contracts.configs import Configs
    configs = get_container().force_fetch(Configs)
    return configs.get(AppConf)


@st.cache_resource
def get_app_docs() -> Documents:
    conf = get_app_conf()
    registry = get_container().force_fetch(DocumentRegistry)
    return registry.get_domain(conf.domain, conf.lang)
