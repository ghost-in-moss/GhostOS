from __future__ import annotations
from typing import Optional, Dict

from ghostos.abcd import Conversation
from ghostos.abcd.realtime import (
    Realtime, RealtimeConfig, RealtimeDriver, Listener, Speaker, RealtimeAppConfig,
    RealtimeApp,
)
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.configs import YamlConfig, Configs
from ghostos_container import Container, Provider, INSTANCE


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
        driver: RealtimeDriver | None = self._drivers.get(config.driver_name())
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
        logger = con.force_fetch(LoggerItf)
        realtime = ConfigsBasedRealtime(configs)
        try:
            from ghostos.framework.openai_realtime.driver import OpenAIRealtimeDriver
            realtime.register(OpenAIRealtimeDriver())
        except ImportError:
            OpenAIRealtimeDriver = None
            logger.info(f"failed to import OpenAIRealtimeDriver")
        finally:
            return realtime
