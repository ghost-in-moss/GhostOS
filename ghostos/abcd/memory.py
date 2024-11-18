from abc import ABC, abstractmethod
from typing import Type, Iterable
from ghostos.entity import EntityClass
from ghostos.identifier import Identifier, Identical
from .concepts import Scope


class Memory(EntityClass, Identical, ABC):

    @abstractmethod
    def make_id(self, scope: Scope) -> str:
        """
        memory instance is unique to a certain scope by generate unique id from scope ids.
        :param scope:
        :return:
        """
        pass


class Memories(ABC):

    @abstractmethod
    def match(self, memory_type: Type[Memory]) -> bool:
        pass

    @abstractmethod
    def remember(self, memory: Memory) -> str:
        """
        remember a memory by session scope
        :param memory: memory object
        :return: memory id
        """
        pass

    @abstractmethod
    def find(self, memory_id: str, expect: Type[Memory]) -> Memory:
        """
        find memory by id
        :param memory_id:
        :param expect:
        :return:
        """
        pass

    @abstractmethod
    def recall(self, query: str, top_k: int = 10) -> Iterable[Identifier]:
        pass


class MemoryRepository(Memories, ABC):

    @abstractmethod
    def register(self, driver: Memories) -> None:
        pass
