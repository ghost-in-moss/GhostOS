from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Type, List, Generic, TypeVar, Any
from pydantic import BaseModel
from ghostiss.core.promptable import PromptAbleClass, PromptAbleObject

if TYPE_CHECKING:
    from ghostiss.context import Context
    from ghostiss.core.ghosts.ghost import Ghost


class Libraries(ABC):
    pass
