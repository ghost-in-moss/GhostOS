from ghostos.prototypes.streamlitapp.main import main_run, SINGLETONS
from ghostos.prototypes.streamlitapp.utils.session import Singleton


def bootstrap() -> SINGLETONS:
    from os.path import dirname
    from ghostos.bootstrap import make_app_container
    from ghostos.prototypes.streamlitapp.pages.router import default_router

    app_dir = dirname(__file__)
    app_container = make_app_container(app_dir)

    # bind container before everything
    yield Singleton(app_container)
    yield Singleton(default_router())


main_run(bootstrap)
