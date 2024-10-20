from typing import Optional, List
from ghostos.prototypes.streamlitapp.utils.route import Route, Router, Link
from ghostos.core.messages import Message
from ghostos.core.aifunc import ExecFrame
from enum import Enum
from pydantic import Field


class PagePath(str, Enum):
    HOMEPAGE = "ghostos.prototypes.streamlitapp.pages.homepage"
    AIFUNCS = "ghostos.prototypes.streamlitapp.pages.aifuncs"

    def suffix(self, attr_name: str):
        return self.value + attr_name


# --- home --- #

class Home(Route):
    link = Link(
        name="Home",
        import_path=PagePath.HOMEPAGE.suffix(":home"),
        streamlit_icon=":material/home:",
        button_help="help",
        antd_icon="house-fill",
    )


class Navigator(Route):
    link = Link(
        name="Navigator",
        import_path=PagePath.HOMEPAGE.suffix(":navigator"),
        streamlit_icon=":material/home:",
        antd_icon="box-fill",
    )


class GhostOSHost(Route):
    link = Link(
        name="GhostOS Host",
        import_path=PagePath.HOMEPAGE.suffix(":ghostos_host"),
        streamlit_icon=":material/smart_toy:",
    )


class Helloworld(Route):
    """
    test only
    """
    link = Link(
        name="Hello World",
        import_path=PagePath.HOMEPAGE.suffix(":helloworld"),
        streamlit_icon=":material/home:",
    )


# --- ai functions --- #

class AIFuncListRoute(Route):
    link = Link(
        name="AIFunc List",
        import_path=PagePath.AIFUNCS.suffix(".index:main"),
        streamlit_icon=":material/functions:",
    )
    search: str = Field(
        default="",
        description="search ai functions with keyword",
    )


class AIFuncDetailRoute(Route):
    link = Link(
        name="AIFunc Detail",
        import_path=PagePath.AIFUNCS.suffix(".detail:main"),
        streamlit_icon=":material/functions:",
    )
    aifunc_id: str = Field(
        default="",
        description="AIFunc ID, which is import path of it",
    )
    frame: Optional[ExecFrame] = Field(
        default=None,
        description="current execution frame",
    )
    executed: bool = False
    received: List[Message] = Field(
        default_factory=list,
        description="list of execution messages",
    )
    timeout: float = 40
    exec_idle: float = 0.2

    def clear_execution(self):
        self.executed = False
        self.received = []
        self.frame = None


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
