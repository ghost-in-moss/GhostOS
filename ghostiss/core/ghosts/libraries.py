from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Type, List, Generic, TypeVar, Any
from pydantic import BaseModel
from ghostiss.core.promptable import PromptAbleClass, PromptAbleObject

if TYPE_CHECKING:
    from ghostiss.context import Context
    from ghostiss.core.ghosts.ghost import Ghost


class Driver(PromptAbleClass, PromptAbleObject, ABC):
    pass


R = TypeVar('R', bound=BaseModel)


class Caller(Generic[R], BaseModel, ABC):
    pass


C = TypeVar('C', bound=Caller)


class Tool(Generic[C, R], ABC):

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def caller(self) -> Type[C]:
        pass

    def callback(self, ctx: "Context", g: "Ghost", arguments: Dict) -> R:
        pass


class Libraries(ABC):

    def get_drivers(self, types: Dict[str, Type[Driver]]) -> Dict[str, Driver]:
        pass

    def get_tools(self, names: List[str]) -> Dict[str, Tool]:
        pass

    def run_tool(self, caller: Caller) -> Any:
        pass
