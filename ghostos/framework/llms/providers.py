from typing import Type, Optional

from ghostos.contracts.configs import YamlConfig, Configs
from ghostos.container import Provider, Container
from ghostos.core.llms import LLMs, LLMsConfig
from ghostos.framework.llms.llms import LLMsImpl
from ghostos.framework.llms.openai_driver import OpenAIDriver

__all__ = ['ConfigBasedLLMsProvider']


class ConfigBasedLLMsProvider(Provider[LLMs]):
    """
    基于 Config 来读取
    """

    def __init__(self, llm_conf_path: str):
        self.llm_conf_path = llm_conf_path

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[LLMs]:
        return LLMs

    def factory(self, con: Container) -> Optional[LLMs]:
        class LLMsYamlConfig(YamlConfig, LLMsConfig):
            """
            配置项存储位置.
            详细配置项见 LLMsConfig
            """
            relative_path = self.llm_conf_path

        configs = con.force_fetch(Configs)
        conf = configs.get(LLMsYamlConfig)
        openai_driver = OpenAIDriver()
        llms = LLMsImpl(conf=conf, default_driver=openai_driver)
        llms.register_driver(openai_driver)
        return llms
