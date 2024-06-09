from abc import ABC, abstractmethod
from typing import Union, Optional
from ghostiss.meta import Meta, MetaData


class Queue(ABC):
    """
    todo: 学习 queue 的实现.
    """

    @abstractmethod
    def put(self, item: Union[Meta, MetaData]) -> None:
        pass

    @abstractmethod
    def pop(self) -> Optional[MetaData]:
        pass


class Queues(ABC):

    @abstractmethod
    def get_kind_queue(self, kind: str) -> Queue:
        pass

    @abstractmethod
    def get_topic_queue(self, kind: str, topic: str) -> Queue:
        pass
