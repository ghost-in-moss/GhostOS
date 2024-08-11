from typing import TYPE_CHECKING, Optional
from abc import ABC, abstractmethod
from ghostiss.entity import Entity, EntityFactory, EntityMeta
from ghostiss.container import Container
from ghostiss.abc import Descriptive, Identifiable
from ghostiss.core.ghosts.shells import Shell
from ghostiss.core.messages.message import MessageType, MessageTypeParser

from ghostiss.core.session import Session, EventBus
from ghostiss.contracts.logger import LoggerItf
from ghostiss.core.ghosts.thoughts import Mindset
from ghostiss.core.ghosts.minds import MultiTasks, Mindflow

__all__ = ['Ghost', 'Facade']


class Ghost(Entity, Descriptive, Identifiable, ABC):

    def get_description(self) -> str:
        """
        ghost 实例的描述. 用于外部系统.
        """
        return self.identifier().get_description()

    @property
    @abstractmethod
    def container(self) -> Container:
        """
        ghost 持有的 IoC 容器.
        """
        pass

    @abstractmethod
    def session(self) -> Session:
        pass

    @property
    def shell(self) -> Shell:
        """
        返回 ghost 所属的 shell 抽象. 本质上也是 unsafe 的.
        """
        return self.container.force_fetch(Shell)

    @property
    @abstractmethod
    def mindset(self) -> "Mindset":
        """
        ghost 可以管理的所有 Thoughts.
        """
        pass

    @property
    @abstractmethod
    def modules(self) -> "Modules":
        """
        基于 modules 可以动态 import 各种库.
        """
        pass

    @property
    @abstractmethod
    def eventbus(self) -> "EventBus":
        """
        用来管理事件通讯.
        """
        pass

    @property
    @abstractmethod
    def logger(self) -> "LoggerItf":
        """
        返回基于当前上下文生成的 logger 实例.
        """
        pass

    @abstractmethod
    def meta_prompt(self) -> str:
        """
        ghost 动态生成自己的 meta prompt.
        """
        pass

    @abstractmethod
    def taskmanager(self) -> "Mindflow":
        pass

    @abstractmethod
    def multitasks(self) -> "MultiTasks":
        pass

    @abstractmethod
    def facade(self) -> "Facade":
        pass

    @abstractmethod
    def finish(self, err: Optional[Exception]) -> None:
        pass

    @abstractmethod
    def destroy(self) -> None:
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


class Facade:
    """
    基于 ghost 抽象可以实现的各种基础功能, 放到 facade 里.
    """

    def __init__(self, ghost: Ghost):
        self.ghost = ghost

    def send(self, *messages: MessageType) -> None:
        """
        发送多条消息. 并且把消息直接加入到当前的 Thread 中间.
        todo: move to session
        """
        parser = MessageTypeParser()
        session = self.ghost.session
        thread = session.thread()
        messenger = self.ghost.messenger().new(thread=thread)
        iterator = parser.parse(messages)
        for msg in iterator:
            messenger.deliver(msg)

        messages, _ = messenger.flush()
        session.update_thread(thread)


class GhostFactory(EntityFactory[Ghost], ABC):

    def register(self, ghost_meta: EntityMeta) -> None:
        pass

    def force_new_ghost(self, meta: EntityMeta) -> Ghost:
        return self.force_new_entity(meta)
