from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class Descriptive(ABC):

    @abstractmethod
    def get_description(self) -> str:
        pass


class Identifier(BaseModel):
    id: str = Field(default="", description="Unique identifier")
    name: str = Field(default="", description="Name of the object")
    description: str = Field(default="", description="Description of the object")


class Identifiable(ABC):
    """
    描述一个可识别的对象.
    """

    @abstractmethod
    def identifier(self) -> Identifier:
        pass


class PromptAble(ABC):
    """
    拥有 __prompt__ 方法的类.
    这里只是一个示范, 并不需要真正继承这个类, 只需要有 __prompt__ 方法或属性.
    """

    def __prompt__(self) -> str:
        pass


class PromptAbleClass(ABC):

    def __class_prompt__(self) -> str:
        pass
