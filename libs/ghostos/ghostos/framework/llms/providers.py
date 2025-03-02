from typing import Type, Optional
from ghostos.contracts.configs import YamlConfig, Configs
from ghostos_container import Provider, Container
from ghostos.core.llms import LLMs, LLMsConfig, PromptStorage
from ghostos.core.messages.openai import OpenAIMessageParser
from ghostos.framework.llms.llms import LLMsImpl
from ghostos.framework.llms.openai_driver import OpenAIDriver
from ghostos.framework.llms.lite_llm_driver import LiteLLMDriver
from ghostos.framework.llms.deepseek_driver import DeepseekDriver
from ghostos.framework.llms.prompt_storage_impl import PromptStorageImpl
from ghostos.contracts.workspace import Workspace
from ghostos.contracts.logger import LoggerItf

__all__ = ['ConfigBasedLLMsProvider', 'PromptStorageInWorkspaceProvider', 'LLMsYamlConfig']


class LLMsYamlConfig(YamlConfig, LLMsConfig):
    """
    LLMs Service and Models configurations.
    """
    relative_path = "llms_conf.yml"


class ConfigBasedLLMsProvider(Provider[LLMs]):
    """
    基于 Config 来读取
    """

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[LLMs]:
        return LLMs

    def factory(self, con: Container) -> Optional[LLMs]:
        configs = con.force_fetch(Configs)
        storage = con.force_fetch(PromptStorage)
        parser = con.get(OpenAIMessageParser)
        logger: LoggerItf = con.force_fetch(LoggerItf)

        conf = configs.get(LLMsYamlConfig)
        openai_driver = OpenAIDriver(storage, logger, parser)
        lite_llm_driver = LiteLLMDriver(storage, logger, parser)
        deepseek_driver = DeepseekDriver(storage, logger, parser)

        # register default drivers.
        llms = LLMsImpl(conf=conf, default_driver=openai_driver)
        llms.register_driver(openai_driver)
        llms.register_driver(lite_llm_driver)
        llms.register_driver(deepseek_driver)

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
