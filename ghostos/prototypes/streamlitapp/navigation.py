from ghostos.prototypes.streamlitapp.utils.route import Route, Router, Link
from ghostos.prototypes.streamlitapp.pages import homepage
from enum import Enum


class PagePath(str, Enum):
    HOMEPAGE = "ghostos.prototypes.streamlitapp.pages.homepage"

    def spec(self, attr_name: str):
        return self.value + ':' + attr_name


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


default_router = Router(
    [
        Home(),
        Helloworld(),
        Navigator(),
        GhostOSHost(),
    ],
    home=Home.label(),
    navigator_names=[
        GhostOSHost.label(),
        Helloworld.label(),
    ],
    default_menu={
        Home.label(): None,
        Helloworld.label(): None,
    },
    default_sidebar_buttons=[
    ],
)
