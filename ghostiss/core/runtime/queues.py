from abc import ABC, abstractmethod
from typing import Union, Optional
from ghostiss.entity import Entity, EntityMeta, EntityDriver


class Queue(ABC):
    """
    todo: 学习 queue 的实现.
    """

    def put(self, item: Union[Entity, EntityDriver, EntityMeta]) -> None:
        """
        sugar
        """
        if isinstance(item, Entity):
            item = item.to_entity_meta()
        elif isinstance(item, EntityDriver):
            item = item.get_meta().to_entity_meta()
        return self._put(item)

    @abstractmethod
    def _put(self, item: EntityMeta) -> None:
        pass

    @abstractmethod
    def pop(self) -> Optional[EntityMeta]:
        pass


class Queues(ABC):

    @abstractmethod
    def get_kind_queue(self, kind: str) -> Queue:
        pass

    @abstractmethod
    def get_topic_queue(self, kind: str, topic: str) -> Queue:
        pass
