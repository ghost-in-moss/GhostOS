from typing import Optional, Dict, Iterator, Tuple, List
from os import environ

from ghostiss.blueprint.kernel.llms import LLMs, LLMApi, ServiceConf, ModelConf, LLMDriver, LLMsConfig

__all__ = ['LLMsImpl']


class LLMsImpl(LLMs):
    """
    实现 LLMs
    """

    def __init__(
            self,
            *,
            conf: Optional[LLMsConfig],
            default_driver: LLMDriver,
            drivers: Optional[List[LLMDriver]] = None,
    ):
        self.llm_drivers: Dict[str, LLMDriver] = {}
        self.llm_services: Dict[str, ServiceConf] = {}
        self.llm_models: Dict[str, ModelConf] = {}
        self.default_driver = default_driver
        if drivers:
            for driver in drivers:
                self.register_driver(driver)
        if conf:
            for service in conf.services:
                self.register_service(service)
            for name, model in conf.models.items():
                self.register_model(name, model)

    def register_driver(self, driver: LLMDriver) -> None:
        self.llm_drivers[driver.driver_name()] = driver

    def register_service(self, service: ServiceConf) -> None:
        if not service.token:
            service.token = self._get_token(service.token_key)
        self.llm_services[service.name] = service

    @staticmethod
    def _get_token(token_key: str) -> str:
        """
        默认使用 env 来获取.
        """
        return environ.get(token_key)

    def register_model(self, name: str, model_conf: ModelConf) -> None:
        self.llm_models[name] = model_conf

    def services(self) -> List[ServiceConf]:
        return list(self.llm_services.values())

    def each_api_conf(self) -> Iterator[Tuple[ServiceConf, ModelConf]]:
        for model_conf in self.llm_models.values():
            service = self.llm_services.get(model_conf.service, None)
            if service is None:
                # todo: 似乎要 fail.
                continue
            yield service, model_conf

    def new_api(self, service_conf: ServiceConf, api_conf: ModelConf) -> LLMApi:
        driver = self.llm_drivers.get(service_conf.driver, self.default_driver)
        return driver.new(service_conf, api_conf)

    def get_api(self, api_name: str, trace: Optional[Dict] = None) -> Optional[LLMApi]:
        model_conf = self.llm_models.get(api_name, None)
        if model_conf is None:
            return None
        service_conf = self.llm_services.get(model_conf.service, None)
        if service_conf is None:
            return None
        return self.new_api(service_conf, model_conf)
