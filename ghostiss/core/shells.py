from abc import ABC, abstractmethod

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Type
from ghostiss.entity import EntityMeta, EntityClass
from ghostiss.entity import Entity, EntityFactory
from ghostiss.core.messages.messenger import Deliver

__all__ = ['Shell', 'ShellFactory', 'Driver', 'App', 'Envs']


class Envs(BaseModel):
    description: str = Field(default="", description="对 ghost 所处环境的描述.")
    trace: Dict = Field(default_factory=dict, description="通讯参数.")
    objects: List[EntityMeta] = Field(
        default_factory=list,
        description="环境中各种物体的元数据. 协议不对齐时, 无法理解环境.",
    )

    __objects: Optional[Dict[str, EntityMeta]] = None

    def __map(self):
        if self.__objects is not None:
            return
        self.__objects = {}
        for o in self.objects:
            self.__objects[o["type"]] = o

    def get_meta(self, cls: Type[EntityClass]) -> Optional[EntityClass]:
        self.__map()
        data = self.get_object_meta(cls.entity_type())
        if data is None:
            return None
        return cls.new_entity(data)

    def get_object_meta(self, meta_kind: str) -> Optional[EntityMeta]:
        self.__map()
        return self.__objects.get(meta_kind, None)


class Driver(ABC):
    """
    可以实现的抽象驱动.
    """

    @classmethod
    @abstractmethod
    def description(cls) -> str:
        pass


class App(ABC):
    """
    自解释的 app.
    """

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass


class Shell(ABC):

    @abstractmethod
    def id(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def get_drivers(self, drivers: List[Type[Driver]]) -> Dict[str, Driver]:
        pass

    @abstractmethod
    def get_apps(self) -> List[App]:
        pass

    @abstractmethod
    def deliver(self) -> Deliver:
        """
        消息发送管道.
        """
        pass


class ShellFactory(EntityFactory[Shell], ABC):
    pass
