import os

import yaml

from ghostos_container import Container
from ghostos.core.llms import LLMsConfig, ServiceConf, ModelConf, LLMs
from ghostos.contracts.configs import YamlConfig, Configs
from ghostos.framework.configs import ConfigsByStorageProvider
from ghostos.framework.storage import MemStorage, Storage
from ghostos.framework.logger import LoggerItf, FakeLogger
from ghostos.framework.llms import ConfigBasedLLMsProvider, PromptStorage, PromptStorageImpl


def _prepare_container() -> Container:
    container = Container()
    storage = MemStorage()
    container.set(LoggerItf, FakeLogger())
    container.set(Storage, storage)
    container.register(ConfigsByStorageProvider('configs'))
    container.set(PromptStorage, PromptStorageImpl(storage.sub_storage("prompts")))

    data = LLMsConfig(
        services=[
            ServiceConf(
                name='moonshot',
                base_url="http://moonshot.com",
                token="$MOONSHOT_TOKEN",
            )
        ],
        default="moonshot-v1-32k",
        models={
            "moonshot-v1-32k": ModelConf(
                model="moonshot-v1-32k",
                service="moonshot"
            ),
            "gpt-4": dict(
                model="moonshot-v1-32k",
                service="moonshot"
            )
        }
    )

    storage.put("configs/llms_conf.yml", yaml.safe_dump(data.model_dump()).encode())
    return container


def test_load_llms_conf():
    container: Container = _prepare_container()

    class LLMsYamlConf(YamlConfig, LLMsConfig):
        relative_path = "llms_conf.yml"

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
    container.register(ConfigBasedLLMsProvider())

    llms = container.force_fetch(LLMs)
    api = llms.get_api("gpt-4")
    assert api is not None

    api2 = llms.force_get_api("moonshot-v1-32k")
    assert api2 is not None

    assert api2.get_service().name == "moonshot"
    assert api2.get_model().model == "moonshot-v1-32k"
