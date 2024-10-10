from typing import Type, Optional
from ghostos.contracts.configs import Configs, Config, C
from abc import ABC, abstractmethod


class BasicConfigs(Configs, ABC):
    """
    A Configs(repository) based on Storage, no matter what the Storage is.
    """

    def get(self, conf_type: Type[C], relative_path: Optional[str] = None) -> C:
        path = conf_type.conf_path()
        relative_path = relative_path if relative_path else path
        content = self._get(relative_path)
        return conf_type.unmarshal(content)

    @abstractmethod
    def _get(self, relative_path: str) -> bytes:
        pass

    @abstractmethod
    def _put(self, relative_path: str, content: bytes) -> None:
        pass

    def save(self, conf: Config, relative_path: Optional[str] = None) -> None:
        marshaled = conf.marshal()
        relative_path = relative_path if relative_path else conf.conf_path()
        self._put(relative_path, marshaled)
