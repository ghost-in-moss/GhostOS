from typing import Optional, Dict, Tuple, List

from enum import Enum
from pydantic import Field
import streamlit as st
from ghostos.container import Container
from ghostos.prototypes.streamlitapp.utils.session import Singleton
from ghostos.contracts.configs import YamlConfig, Configs
from ghostos.contracts.assets import ImageAssets, FileInfo, AudioAssets
from ghostos.contracts.documents import DocumentRegistry, Documents
from PIL.Image import Image as ImageType
from ghostos.core.messages.message_classes import ImageAssetMessage
from ghostos.helpers import GHOSTOS_DOMAIN, uuid
from streamlit.runtime.uploaded_file_manager import DeletedFile, UploadedFile


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


@st.cache_resource
def get_images_assets() -> ImageAssets:
    container = get_container()
    return container.force_fetch(ImageAssets)


@st.cache_resource
def get_audio_assets() -> AudioAssets:
    container = get_container()
    return container.force_fetch(AudioAssets)


def save_uploaded_image(file: UploadedFile) -> FileInfo:
    image_info = FileInfo(
        fileid=file.file_id,
        filename=file.name,
        description="streamlit camera input",
        filetype=file.type,
    )
    binary = file.getvalue()
    save_image_info(image_info, binary)
    return image_info


def save_image_info(image_info: FileInfo, binary: bytes) -> None:
    assets = get_images_assets()
    assets.save(image_info, binary)


def save_pil_image(image: ImageType, desc: str) -> FileInfo:
    from io import BytesIO
    file_id = uuid()
    img_bytes = BytesIO()
    image.save(img_bytes, format='PNG')
    binary = img_bytes.getvalue()
    image_info = FileInfo(
        image_id=file_id,
        filename=file_id + ".png",
        filetype="image/png",
        description=desc
    )
    save_image_info(image_info, binary)
    return image_info


def get_images_from_image_asset(image_ids: List[str]) -> Dict[str, Tuple[FileInfo, Optional[bytes]]]:
    result = {}
    assets = get_images_assets()
    for image_id in image_ids:
        data = assets.get_file_and_binary_by_id(image_id)
        if data is None:
            continue
        result[image_id] = data
    return result
