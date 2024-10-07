import yaml
from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar, Type, Optional, AnyStr
from pydantic import BaseModel

__all__ = ['Config', 'Configs', 'YamlConfig', 'C']


class Config(ABC):
    """
    Configuration class for something.
    Once it implements the Config interface,
    It could be managed by Configs.
    """

    @classmethod
    @abstractmethod
    def conf_path(cls) -> str:
        """
        relative path to the Configs.
        notice the Configs is not always based on FileSystem, so the path is also abstract identity of the conf.
        """
        pass

    @classmethod
    @abstractmethod
    def load(cls, content: AnyStr) -> "Config":
        """
        unmarshal the Config instance from content.
        todo: rename it to unmarshal, and add marshal method.
        """
        pass


C = TypeVar('C', bound=Config)


class Configs(ABC):
    """
    Repository for variable kinds of Config.
    Treat all the configs as a data object
    todo: we still need save method.
    """

    @abstractmethod
    def get(self, conf_type: Type[C], relative_path: Optional[str] = None) -> C:
        """
        get a Config instance or throw exception
        :param conf_type: the Config class that shall unmarshal the config data
        :param relative_path: the relative path of the config data, if pass, override the conf_type default path.
        :return: instance of the Config.
        :exception: FileNotFoundError
        """
        pass


TIP = """
With object class Config and repository class Configs, 
we decoupled the Model and IO of a Config system. 

When defining a Config Model, we never think about where to put it (file system or cloud object storage).
"""


class YamlConfig(Config, BaseModel):
    """
    Use Pydantic BaseModel to define a Config class.
    And marshal the data to yaml.
    todo: rename to YamlConfigModel
    """

    relative_path: ClassVar[str]

    @classmethod
    def conf_path(cls) -> str:
        return cls.relative_path

    @classmethod
    def load(cls, content: str) -> "Config":
        value = yaml.safe_load(content)
        return cls(**value)

# todo: toml config
