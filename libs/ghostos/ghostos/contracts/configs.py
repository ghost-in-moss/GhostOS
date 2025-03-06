import yaml
from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar, Type, Optional
from typing_extensions import Self
from pydantic import BaseModel
from ghostos_common.helpers import generate_import_path

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
    def unmarshal(cls, content: bytes) -> Self:
        """
        unmarshal the Config instance from content.
        """
        pass

    def marshal(self) -> bytes:
        """
        marshal self to a savable content
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

    @abstractmethod
    def get_or_create(self, conf: C) -> C:
        pass

    @abstractmethod
    def save(self, conf: Config, relative_path: Optional[str] = None) -> None:
        """
        save a Config instance to it source.
        notice some config shall be immutable
        :param conf: the conf object
        :param relative_path: if pass, override the conf_type default path.
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
    def unmarshal(cls, content: str) -> Self:
        value = yaml.safe_load(content)
        return cls(**value)

    def marshal(self) -> bytes:
        value = self.model_dump(exclude_defaults=True)
        comment = f"# from class: {generate_import_path(self.__class__)}"
        result = yaml.safe_dump(value)
        return "\n".join([comment, result]).encode()
