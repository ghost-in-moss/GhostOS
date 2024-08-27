import os
from ghostos.container import Container
from ghostos.core.llms import LLMsConfig, LLMs
from ghostos.contracts.configs import YamlConfig, ConfigsByStorageProvider, Configs
from ghostos.framework.storage import FileStorageProvider
from ghostos.framework.llms import ConfigBasedLLMsProvider


def _prepare_container() -> Container:
    dirname = os.path.dirname
    demo_dir = dirname(__file__) + "/../../../demo/ghostos"
    demo_dir = os.path.abspath(demo_dir)
    container = Container()
    container.register(FileStorageProvider(demo_dir))
    container.register(ConfigsByStorageProvider('configs'))
    return container


def test_load_llms_conf():
    container: Container = _prepare_container()

    class LLMsYamlConf(YamlConfig, LLMsConfig):
        relative_path = "llms/test_llms_conf.yaml"

    configs = container.get(Configs)
    conf = configs.get(LLMsYamlConf)
    assert len(conf.services) > 0

    moonshot = conf.services[0]
    assert moonshot.name == "moonshot"
    assert moonshot.token.startswith('$')

    data = {moonshot.token[1:]: "test"}
    moonshot.load(environ=data)
    assert moonshot.token == "test"


def test_llms():
    """
    存在文件依赖关系.
    """
    container: Container = _prepare_container()
    container.register(ConfigBasedLLMsProvider("llms/test_llms_conf.yaml"))

    llms = container.force_fetch(LLMs)
    api = llms.get_api("test")
    assert api is not None

    api2 = llms.force_get_api("test")
    assert api2 is not None

    assert api2.get_service().name == "moonshot"
    assert api2.get_model().model == "v1"
