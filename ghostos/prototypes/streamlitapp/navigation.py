from typing import Optional, List
from ghostos.prototypes.streamlitapp.utils.route import Route, Router, Link
from ghostos.prototypes.streamlitapp.pages import homepage
from ghostos.core.messages import Message
from ghostos.core.aifunc import ExecFrame
from enum import Enum
from pydantic import Field
from ghostos.entity import EntityMeta


class PagePath(str, Enum):
    HOMEPAGE = "ghostos.prototypes.streamlitapp.pages.homepage"
    AIFUNCS = "ghostos.prototypes.streamlitapp.pages.aifuncs"

    def spec(self, attr_name: str):
        return self.value + ':' + attr_name


# --- home --- #

class Home(Route):
    link = Link(
        name="Home",
        import_path=PagePath.HOMEPAGE.spec("home"),
        streamlit_icon=":material/home:",
        button_help="help",
        antd_icon="house-fill",
    )


class Navigator(Route):
    link = Link(
        name="Navigator",
        import_path=PagePath.HOMEPAGE.spec("navigator"),
        streamlit_icon=":material/home:",
        antd_icon="box-fill",
    )


class GhostOSHost(Route):
    link = Link(
        name="GhostOS Host",
        import_path=PagePath.HOMEPAGE.spec("ghostos_host"),
        streamlit_icon=":material/smart_toy:",
    )


class Helloworld(Route):
    """
    test only
    """
    link = Link(
        name="Hello World",
        import_path=PagePath.HOMEPAGE.spec("helloworld"),
        streamlit_icon=":material/home:",
    )


# --- ai functions --- #

class AIFuncListRoute(Route):
    link = Link(
        name="AIFunc List",
        import_path=PagePath.AIFUNCS.spec("aifuncs_list"),
        streamlit_icon=":material/functions:",
    )
    search: str = Field(
        default="",
        description="search ai functions with keyword",
    )


class AIFuncDetailRoute(Route):
    link = Link(
        name="AIFunc Detail",
        import_path=PagePath.AIFUNCS.spec("aifunc_detail"),
        streamlit_icon=":material/functions:",
    )
    aifunc_id: str = Field(
        default="",
        description="AIFunc ID, which is import path of it",
    )
    aifunc_meta: Optional[EntityMeta] = Field(
        default=None,
        description="aifuncs metadata",
    )
    frame: Optional[ExecFrame] = Field(
        default=None,
        description="current execution frame",
    )
    messages: List[Message] = Field(
        default_factory=list,
        description="list of execution messages",
    )


# --- routers --- #

def default_router() -> Router:
    return Router(
        [
            Home(),
            Helloworld(),
            Navigator(),
            GhostOSHost(),
            AIFuncListRoute(),
            AIFuncDetailRoute(),
        ],
        home=Home.label(),
        navigator_names=[
            GhostOSHost.label(),
            AIFuncListRoute.label(),
        ],
        default_menu={
            Home.label(): None,
        },
        default_sidebar_buttons=[
        ],
    )
