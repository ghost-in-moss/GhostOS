from ghostos.prototypes.streamlitapp import main_run, Singleton, default_router, ConfigsRoute
from ghostos.bootstrap import get_container


def bootstrap():
    router = default_router().with_current(ConfigsRoute())
    return [
        Singleton(get_container()),
        Singleton(router),
    ]


main_run(bootstrap)
