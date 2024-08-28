from typing import Callable, List, Optional, Type
from abc import ABC, abstractmethod
from ghostos.container import Provider, Container, ABSTRACT


class Shutdown(ABC):
    """
    a registrar to register shutdown callbacks.
    """

    @abstractmethod
    def register(self, shutdown: Callable[[], None]) -> None:
        """
        register a shutdown callback.
        :param shutdown: callback
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        call all the shutdown callbacks.
        """
        pass


class ShutdownImpl(Shutdown):

    def __init__(self):
        self._callbacks: List[Callable[[], None]] = []

    def register(self, shutdown: Callable[[], None]) -> None:
        self._callbacks.append(shutdown)

    def shutdown(self) -> None:
        for callback in self._callbacks:
            callback()
        self._callbacks = []


class ShutdownProvider(Provider[Shutdown]):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Shutdown]:
        return Shutdown

    def factory(self, con: Container) -> Optional[Shutdown]:
        return ShutdownImpl()
