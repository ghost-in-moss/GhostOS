from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from ghostos.helpers import generate_import_path

__all__ = [
    'Descriptive',
    'Identifier', 'Identifiable', 'IdentifiableClass', 'identify_class', 'identify_class_id',
    'PromptAble', 'PromptAbleClass'
]


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


class IdentifiableClass(ABC):

    @classmethod
    @abstractmethod
    def class_identifier(cls) -> Identifier:
        pass


def identify_class(cls: type) -> Identifier:
    """
    一个默认的用来描述类的方法.
    :param cls: 目标类.
    :return: 返回一个 identifier.
    """
    if issubclass(cls, IdentifiableClass):
        return cls.class_identifier()
    id_ = identify_class_id(cls)
    name = cls.__name__
    desc = cls.__doc__
    return Identifier(id=id_, name=name, description=desc)


def identify_class_id(cls: type) -> str:
    return generate_import_path(cls)


class PromptAble(ABC):
    """
    拥有 __prompt__ 方法的类.
    这里只是一个示范, 并不需要真正继承这个类, 只需要有 __prompt__ 方法或属性.
    """

    @abstractmethod
    def __prompt__(self) -> str:
        pass


class PromptAbleClass(ABC):

    @classmethod
    @abstractmethod
    def __class_prompt__(cls) -> str:
        pass
