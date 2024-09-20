from ghostos.container import Container
from ghostos.core.moss import test_container
from ghostos.framework.configs import ConfigsByStorageProvider
from ghostos.framework.storage import FileStorageProvider
from ghostos.framework.llms import ConfigBasedLLMsProvider

__all__ = ["init_ghost_func_container"]


def init_ghost_func_container(
        root_path: str,
        configs_path: str = "configs",
        llm_conf_path: str = "llms_conf.yml",
) -> Container:
    container = test_container()
    container.register(FileStorageProvider(root_path))
    container.register(ConfigsByStorageProvider(configs_path))
    container.register(ConfigBasedLLMsProvider(llm_conf_path))
    return container
