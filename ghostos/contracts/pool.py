from typing import Callable, Optional, Type
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from ghostos.container import Provider, Container, ABSTRACT


class Pool(ABC):
    """
    建一个全局的池.
    """

    @abstractmethod
    def submit(self, caller: Callable, *args, **kwargs) -> Callable:
        pass

    @abstractmethod
    def shutdown(self, wait=True, *, cancel_futures=False):
        pass


class DefaultPool(Pool):
    def __init__(self, size: int):
        self.size = size
        self.pool = ThreadPoolExecutor(max_workers=size)

    def submit(self, caller: Callable, *args, **kwargs) -> None:
        self.pool.submit(caller, *args, **kwargs)

    def shutdown(self, wait=True, *, cancel_futures=False):
        self.pool.shutdown(wait=wait, cancel_futures=cancel_futures)


class DefaultPoolProvider(Provider):

    def __init__(self, size: int = 100):
        self.size = size

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[ABSTRACT]:
        return Pool

    def factory(self, con: Container) -> Optional[ABSTRACT]:
        return DefaultPool(self.size)
