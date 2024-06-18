from abc import ABC, abstractmethod
from typing import Union, Optional
from ghostiss.entity import Entity, Normalized, EntityDriver


class Queue(ABC):
    """
    todo: 学习 queue 的实现.
    """

    def put(self, item: Union[Entity, EntityDriver, Normalized]) -> None:
        """
        sugar
        """
        if isinstance(item, Entity):
            item = item.normalize()
        elif isinstance(item, EntityDriver):
            item = item.get_meta().normalize()
        return self._put(item)

    @abstractmethod
    def _put(self, item: Normalized) -> None:
        pass

    @abstractmethod
    def pop(self) -> Optional[Normalized]:
        pass


class Queues(ABC):

    @abstractmethod
    def get_kind_queue(self, kind: str) -> Queue:
        pass

    @abstractmethod
    def get_topic_queue(self, kind: str, topic: str) -> Queue:
        pass
