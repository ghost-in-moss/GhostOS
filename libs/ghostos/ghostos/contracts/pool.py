from typing import Callable, Optional, Type
from typing_extensions import Self
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, Future
from ghostos_container import Provider, Container


class Pool(ABC):
    """
    abstract class for pools like process pool or thread pool
    """

    @abstractmethod
    def submit(self, caller: Callable, *args, **kwargs) -> Future:
        pass

    @abstractmethod
    def new(self, size: int) -> Self:
        """
        use the same class to create a new pool,
        or split a quota to create a sub pool.
        """
        pass

    @abstractmethod
    def shutdown(self, wait=True, *, cancel_futures=False):
        pass


class DefaultPool(Pool):
    def __init__(self, size: int):
        self.size = size
        self.pool = ThreadPoolExecutor(max_workers=size)

    def submit(self, caller: Callable, *args, **kwargs) -> Future:
        return self.pool.submit(caller, *args, **kwargs)

    def new(self, size: int) -> Self:
        return DefaultPool(size)

    def shutdown(self, wait=True, *, cancel_futures=False):
        self.pool.shutdown(wait=wait, cancel_futures=cancel_futures)


class DefaultPoolProvider(Provider[Pool]):

    def __init__(self, size: int = 100):
        self.size = size

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type:
        return Pool

    def factory(self, con: Container) -> Optional[Pool]:
        p = DefaultPool(self.size)
        con.add_shutdown(p.shutdown)
        return p
