import os
from typing import List
from ghostiss.container import Container
from ghostiss.blueprint.kernel.llms import LLMsConfig
from ghostiss.contracts.configs import YamlConfig, StorageConfigsProvider, Configs
from ghostiss.contracts.storage import FileStorageProvider


def _prepare_container() -> Container:
    container = Container()
    dirname = os.path.dirname
    demo_dir = dirname(dirname(__file__) + "/../../../demo/ghostiss")
    container = Container()
    container.register(FileStorageProvider(demo_dir))
    container.register(StorageConfigsProvider('/configs'))
    return container


def test_load_llms_conf():
    container: Container = _prepare_container()

    class LLMsYamlConf(YamlConfig, LLMsConfig):
        relative_path = "llms/test_llms_conf.yaml"

    configs = container.get(Configs)
    conf = configs.get(LLMsYamlConf)
    assert len(conf.services) > 0
