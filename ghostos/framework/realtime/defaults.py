from typing import Optional, Dict

from ghostos.abcd import Conversation
from ghostos.abcd.realtime import (
    Realtime, RealtimeConfig, RealtimeDriver, Listener, Speaker, RealtimeAppConfig,
    RealtimeApp,
)
from ghostos.contracts.configs import YamlConfig, Configs
from ghostos.container import Container, Provider, INSTANCE
from ghostos.framework.openai_realtime import OpenAIRealtimeDriver


class BasicRealtimeConfig(RealtimeConfig, YamlConfig):
    relative_path = "realtime_conf.yml"


class ConfigsBasedRealtime(Realtime):

    def __init__(self, configs: Configs):
        self._drivers: Dict[str: RealtimeDriver] = {}
        self._configs = configs

    def create(
            self,
            conversation: Conversation,
            listener: Listener,
            speaker: Speaker,
            app_name: str = "",
            config: Optional[RealtimeAppConfig] = None,
    ) -> RealtimeApp:
        realtime_conf = self.get_config()
        if config is None:
            if not app_name:
                app_name = realtime_conf.default
            config = realtime_conf.get_app_conf(app_name)
        if config is None:
            raise NotImplementedError(f"No config for {app_name}")
        driver: RealtimeDriver = self._drivers.get(config.driver_name())
        if driver is None:
            raise NotImplementedError(f"No driver for {config.driver_name()}")
        return driver.create(config, conversation, listener, speaker)

    def get_config(self) -> RealtimeConfig:
        return self._configs.get(BasicRealtimeConfig)

    def register(self, driver: RealtimeDriver):
        self._drivers[driver.driver_name()] = driver


class ConfigBasedRealtimeProvider(Provider[Realtime]):

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[INSTANCE]:
        configs = con.get(Configs)
        realtime = ConfigsBasedRealtime(configs)
        realtime.register(OpenAIRealtimeDriver())
        return realtime
