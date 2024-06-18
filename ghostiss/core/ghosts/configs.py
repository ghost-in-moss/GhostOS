from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar, Type, Dict
from pydantic import BaseModel, Field


class Config(BaseModel, ABC):
    path: ClassVar[str]


CONF_TYPE = TypeVar("CONF_TYPE", bound=Config)


class Configs(ABC):

    def load(self, conf_type: Type[CONF_TYPE]) -> CONF_TYPE:
        """
        从 ghost 自己的配置系统里
        """
        content = self.get_content(conf_type.path)
        return conf_type(**content)

    @abstractmethod
    def get_content(self, relative_conf_path: str) -> Dict:
        pass
