import os
import yaml
from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar, Type, Dict, Optional
from pydantic import BaseModel
from ghostiss.container import Container, Provider, ABSTRACT
from ghostiss.contracts.storage import Storage

__all__ = ['Config', 'Configs', 'YamlConfig', 'StorageConfigs', 'ConfigsByStorageProvider']


class Config(ABC):

    @classmethod
    @abstractmethod
    def conf_path(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def load(cls, content: str) -> "Config":
        """
        """
        pass


C = TypeVar('C', bound=Config)


class Configs(ABC):

    @abstractmethod
    def get(self, conf_type: Type[C], file_name: Optional[str] = None) -> C:
        pass


class YamlConfig(Config, BaseModel):
    """
    通过 yaml 定义的配置.
    """

    relative_path: ClassVar[str]

    @classmethod
    def conf_path(cls) -> str:
        return cls.relative_path

    @classmethod
    def load(cls, content: str) -> "Config":
        value = yaml.safe_load(content)
        return cls(**value)


class StorageConfigs(Configs):
    """
    基于 storage 实现的 configs.
    """

    def __init__(self, storage: Storage, conf_dir: str):
        self._storage = storage
        self._conf_dir = conf_dir

    def get(self, conf_type: Type[C], file_name: Optional[str] = None) -> C:
        path = conf_type.conf_path()
        file_path = os.path.join(self._conf_dir, path)
        if file_name is not None:
            file_path = os.path.join(file_path, file_name)

        content = self._storage.get(file_path)
        return conf_type.load(content)


class ConfigsByStorageProvider(Provider[Configs]):

    def __init__(self, conf_dir: str):
        self._conf_dir = conf_dir

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Configs]:
        return Configs

    def factory(self, con: Container) -> Optional[Configs]:
        storage = con.force_fetch(Storage)
        return StorageConfigs(storage, self._conf_dir)
