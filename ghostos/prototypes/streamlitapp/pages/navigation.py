from ghostos.prototypes.streamlitapp.utils.route import Route, Router, Link


class Home(Route):
    link = Link(
        name="home",
        page="pages/homepages/home.py",
        title="Home",
        icon=":material/home:",
    )


class Helloworld(Route):
    link = Link(
        name="helloworld",
        page="pages/homepages/helloworld.py",
        title="Hello World",
        icon=":material/home:",
    )


navigation = Router(
    [
        Home(),
        Helloworld(),
    ],
    sidebar_buttons=["home", "helloworld"],
)
