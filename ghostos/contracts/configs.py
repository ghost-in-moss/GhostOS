import os
import yaml
from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar, Type, Dict, Optional
from pydantic import BaseModel
from ghostos.container import Container, Provider, ABSTRACT
from ghostos.contracts.storage import Storage

__all__ = ['Config', 'Configs', 'YamlConfig', 'C']


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

