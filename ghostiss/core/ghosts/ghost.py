from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar, List
from ghostiss.meta import Meta, BaseMetaClass, MetaObject, MetaMaker, MetaData, MetaFactory

if TYPE_CHECKING:
    from ghostiss.context import Context
    from ghostiss.container import Container
    from ghostiss.core.messenger import Messenger
    from ghostiss.core.kernel.kernel import Kernel
    from ghostiss.core.ghosts.thinks import Thinks
    from ghostiss.core.ghosts.runtime import Runtime, Task
    from ghostiss.core.ghosts.operators import Operations
    from ghostiss.core.ghosts.shell import Shell
    from ghostiss.core.ghosts.libraries import Libraries, Tool


class GhostMeta(Meta, ABC):
    pass


GHOST_META_TYPE = TypeVar('GHOST_META_TYPE', bound=GhostMeta)


class Ghost(MetaObject[GHOST_META_TYPE], ABC):

    @property
    @abstractmethod
    def id(self) -> str:
        pass

    # --- consciousness --- #

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def instructions(self) -> str:
        pass

    # --- components --- #

    @property
    @abstractmethod
    def container(self) -> 'Container':
        pass

    @property
    @abstractmethod
    def kernel(self) -> 'Kernel':
        pass

    @property
    @abstractmethod
    def thinks(self) -> 'Thinks':
        pass

    @property
    @abstractmethod
    def runtime(self) -> 'Runtime':
        pass

    @property
    @abstractmethod
    def shell(self) -> 'Shell':
        pass

    @property
    @abstractmethod
    def libraries(self) -> 'Libraries':
        pass

    # --- methods --- #

    @abstractmethod
    def operates(self, ctx: "Context", task: "Task") -> Operations:
        pass

    @abstractmethod
    def tools(self) -> List['Tool']:
        pass

    @abstractmethod
    def messenger(self) -> 'Messenger':
        """
        生成一个 messenger 的实例.
        """
        pass

    @abstractmethod
    def sleep(self, seconds: float = 0) -> None:
        pass


G = TypeVar('G', bound=Ghost)


class GhostMaker(Generic[G], MetaMaker[G], ABC):
    pass


class Matrix(MetaFactory[Ghost], ABC):
    pass
