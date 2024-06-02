from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from ghostiss.meta import Meta, MetaData, MetaClass, MetaObject, MetaFactory, MetaRepository
if TYPE_CHECKING:
    from ghostiss.interfaces.ghost import Ghost
    from ghostiss.interfaces.shells import Shell


class SourceCode(Meta, ABC):
    pass


class Agent(MetaObject[SourceCode], ABC):

    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def ghost(self) -> Ghost:
        pass

    @property
    @abstractmethod
    def shell(self) -> Shell:
        pass

    @abstractmethod
    def get_meta(self) -> SourceCode:
        pass


class Matrix(MetaFactory[Agent], MetaRepository[SourceCode], ABC):

    @abstractmethod
    def forge(self, meta_data: MetaData) -> Agent:
        return self.factory(meta_data)
