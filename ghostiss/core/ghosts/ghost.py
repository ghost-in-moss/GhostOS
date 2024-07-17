from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
from ghostiss.entity import Entity, EntityFactory, EntityMeta
from ghostiss.container import Container
from ghostiss.core.moss.reflect import Descriptive

if TYPE_CHECKING:
    from ghostiss.contracts.logger import LoggerItf
    from ghostiss.core.runtime.runtime import Runtime
    from ghostiss.core.ghosts.events import EventBus
    from ghostiss.core.ghosts.session import Session
    from ghostiss.core.moss.moss import MOSS
    from ghostiss.core.shells.shell import Shell
    from ghostiss.core.shells.messenger import Messenger


class Ghost(Entity, Descriptive, ABC):

    @abstractmethod
    def id(self) -> str:
        pass

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    def runtime(self) -> "Runtime":
        """
        提供 runtime 的基建调用, 本质上是 unsafe 的.
        """
        pass

    @abstractmethod
    def shell(self) -> "Shell":
        """
        返回 ghost 所属的 shell 抽象.
        """
        pass

    @abstractmethod
    def session(self) -> "Session":
        pass

    @abstractmethod
    def logger(self) -> LoggerItf:
        pass

    @abstractmethod
    def system_prompt(self) -> str:
        """
        ghost 动态生成自己的 system prompt.
        """
        pass

    @abstractmethod
    def moss(self) -> "MOSS":
        """
        ghost 实例化自己的通用 MOSS
        每次创建一个新的实例.
        """
        pass

    @abstractmethod
    def eventbus(self) -> "EventBus":
        pass

    @abstractmethod
    def messenger(self) -> "Messenger":
        """
        ghost 生成一个 Messenger 供下游处理消息
        """
        pass


class Matrix(EntityFactory[Ghost], ABC):
    """
    ghost factory
    """

    def force_new_ghost(self, meta: EntityMeta) -> "Ghost":
        g = self.new_entity(meta)
        if g is None:
            raise NotImplementedError(f"Ghost initialize failed for {meta}")
        return g
