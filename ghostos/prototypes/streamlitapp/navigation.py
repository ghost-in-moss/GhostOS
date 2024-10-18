from ghostos.prototypes.streamlitapp.utils.route import Route, Router, Link
from ghostos.prototypes.streamlitapp.pages import homepage
from enum import Enum
from pydantic import Field


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


# --- routers --- #

def default_router() -> Router:
    return Router(
[
            Home(),
            Helloworld(),
            Navigator(),
            GhostOSHost(),
            AIFuncListRoute(),
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
