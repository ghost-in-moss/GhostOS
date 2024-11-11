from typing import Type, Optional

from ghostos.contracts.configs import YamlConfig, Configs
from ghostos.container import Provider, Container
from ghostos.core.llms import LLMs, LLMsConfig, PromptStorage
from ghostos.framework.llms.llms import LLMsImpl
from ghostos.framework.llms.openai_driver import OpenAIDriver, LiteLLMDriver
from ghostos.framework.llms.prompt_storage_impl import PromptStorageImpl
from ghostos.contracts.workspace import Workspace

__all__ = ['ConfigBasedLLMsProvider', 'PromptStorageInWorkspaceProvider']


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
        storage = con.force_fetch(PromptStorage)

        conf = configs.get(LLMsYamlConfig)
        openai_driver = OpenAIDriver(storage)
        lite_llm_driver = LiteLLMDriver(storage)

        # register default drivers.
        llms = LLMsImpl(conf=conf, default_driver=openai_driver)
        llms.register_driver(openai_driver)
        llms.register_driver(lite_llm_driver)

        return llms


class PromptStorageInWorkspaceProvider(Provider[PromptStorage]):
    def __init__(self, relative_path: str = "prompts"):
        self._relative_path = relative_path

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[PromptStorage]:
        ws = con.force_fetch(Workspace)
        storage = ws.runtime().sub_storage(self._relative_path)
        return PromptStorageImpl(storage)
