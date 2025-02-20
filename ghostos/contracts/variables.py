from typing import Union, TypeVar, Type, Optional, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from ghostos_common.entity import EntityType

T = TypeVar("T", bound=object)

__all__ = ['Variables']


class Variables(ABC):
    """
    global library that save value to a pointer,
    by the vid can get the value instance further.
    """

    class Var(BaseModel):
        """
        unique pointer of a variable
        """
        vid: str = Field(description="unique variable id")
        type: str = Field(description="variable class type")
        desc: str = Field(description="description about the variable")

    @abstractmethod
    def save(
            self,
            val: Union[BaseModel, dict, list, str, int, float, bool, EntityType, Any],
            desc: str = "",
    ) -> Var:
        """
        save a value and get a Var pointer, with vid can get its instance by load
        :param val: a value that is serializable, at least can be serialized by pickle
        :param desc: description about the variable, save to Var pointer
        :return: the pointer of the value
        """
        pass

    @abstractmethod
    def load(self, vid: str, expect: Optional[Type[T]] = None, force: bool = False) -> Optional[T]:
        """
        load a saved value by vid.
        :param vid: unique variable id in the Var pointer
        :param expect: if the expect type is given, throw error if value is not fit
        :param force: if True, raise Error if value is None
        :return: the unmarshalled value instance
        """
        pass
