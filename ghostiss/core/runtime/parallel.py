from typing import Callable, Iterable, Generic, TypeVar, List
from abc import ABC, abstractmethod

R = TypeVar('R')


class Parallel(ABC):

    def run(self, parallel: int, callers: Iterable[Callable[[int], R]]) -> List[R]:
        """

        :param parallel: 并发运行数.
        :param callers: 需要并发执行的闭包.
        :return:
        """
        pass

