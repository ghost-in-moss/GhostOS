from typing import List, Iterable
from typing_extensions import Self
from abc import ABC, abstractmethod
from ghostos_common.identifier import Identical, Identifier


class Documents(Identical, ABC):

    @abstractmethod
    def domain(self) -> str:
        pass

    @abstractmethod
    def with_lang(self, lang: str) -> Self:
        pass

    @abstractmethod
    def directory(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    def __identifier__(self) -> Identifier:
        return Identifier(
            id=self.directory(),
            name=self.domain(),
            description=self.description(),
        )

    @abstractmethod
    def default_lang(self) -> str:
        pass

    @abstractmethod
    def langs(self) -> List[str]:
        pass

    @abstractmethod
    def read(self, filename: str, locale: str = "") -> str:
        pass

    @abstractmethod
    def iterate(self, depth: int = -1) -> Iterable[str]:
        pass


class DocumentRegistry(ABC):

    @abstractmethod
    def get_domain(self, domain: str, lang: str = "") -> Documents:
        pass

    @abstractmethod
    def register(self, domain: Documents) -> None:
        pass

    @abstractmethod
    def list_domains(self) -> Iterable[Identifier]:
        pass
