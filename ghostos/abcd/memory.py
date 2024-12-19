from abc import ABC, abstractmethod
from typing import Type, Iterable
from ghostos.entity import EntityClass
from ghostos.identifier import Identifier, Identical
from ghostos.helpers import generate_import_path
from ghostos.abcd.concepts import Session


class Memory(EntityClass, Identical, ABC):
    """
    memory element
    """

    @abstractmethod
    def make_id(self, session: Session) -> str:
        """
        memory instance is unique to session, usually create unique id from session scope
        :return:
        """
        pass

    @classmethod
    def memory_kind(cls) -> str:
        return generate_import_path(cls)


class Memories(ABC):

    @abstractmethod
    def match(self, memory_kind: str) -> bool:
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
