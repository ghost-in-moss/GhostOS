from __future__ import annotations

import inspect
from typing import (
    List, Self, Union, Callable, Any, Protocol,
)
from abc import ABC, abstractmethod
from types import ModuleType
from ghostos.container import Container
from ghostos.helpers import generate_import_path
import json

from pydantic import BaseModel
from .entity import EntityClass, EntityMeta, from_entity_meta, to_entity_meta

__all__ = [
    'get_defined_prompt',
    'set_prompter', 'set_class_prompter',
    'Prompter',
    'PromptAbleObj', 'PromptAbleClass',
]


def get_defined_prompt(value: Any) -> Union[str, None]:
    attr = get_defined_prompt_attr(value)
    if attr is None:
        return None
    if isinstance(attr, str):
        return attr
    return attr()


def get_defined_prompt_attr(value: Any) -> Union[None, str, Callable[[], str]]:
    if value is None:
        return None
    elif isinstance(value, PromptAbleObj):
        return value.__prompt__

    elif isinstance(value, type):
        if issubclass(value, PromptAbleClass):
            return value.__class_prompt__
        # class without __class_prompt__ is not defined as prompter
        if hasattr(value, "__class_prompt__"):
            return getattr(value, "__class_prompt__")

    elif hasattr(value, "__prompt__"):
        prompter = getattr(value, "__prompt__")
        if inspect.isfunction(value) or inspect.ismethod(value) or hasattr(prompter, '__self__'):
            return prompter
    elif isinstance(value, ModuleType) and '__prompt__' in value.__dict__:
        prompter = value.__dict__['__prompt__']
        return prompter
    return None


def set_prompter(obj: Any, prompter: Union[Callable[[], str], str], force: bool = False) -> None:
    if force or not hasattr(obj, '__prompt__'):
        setattr(obj, '__prompt__', prompter)


def set_class_prompter(cls: type, prompter: Union[Callable[[], str], str], force: bool = False) -> None:
    if hasattr(cls, '__class__prompt__'):
        fn = getattr(cls, '__class_prompt__')
        cls_name = generate_import_path(cls)
        if force or fn.__class_name__ != cls_name:
            pass
        else:
            return
    prompter.__class_name__ = generate_import_path(cls)
    setattr(cls, '__class_prompt__', prompter)


class Prompter(BaseModel, EntityClass, ABC):
    """
    is strong-typed model for runtime alternative properties of a ghost.
    """

    __children__: List[Prompter] = []
    """ children is fractal sub context nodes"""

    def with_children(self, *children: Prompter) -> Prompter:
        self.__children__.extend(children)
        return self

    @abstractmethod
    def self_prompt(self, container: Container, depth: int = 0) -> str:
        """
        generate prompt by self, without children
        :param container:
        :param depth:
        :return:
        """
        pass

    def get_prompt(self, container: Container, depth: int = 0) -> str:
        """
        get prompt with container which provides libraries to generate prompt
        :param container:
        :param depth:
        :return:
        """
        self_prompt = self.self_prompt(container, depth=depth)
        prompts = [self_prompt]
        for child in self.__children__:
            prompts.append(child.get_prompt(container, depth=depth + 1))
        return "\n\n".join([prompt.rstrip() for prompt in prompts])

    def __to_entity_meta__(self) -> EntityMeta:
        type_ = generate_import_path(self.__class__)
        ctx_data = self.model_dump(exclude_defaults=True)
        children_data = []
        for child in self.__children__:
            children_data.append(to_entity_meta(child))
        data = {"ctx": ctx_data, "children": children_data}
        content = json.dumps(data)
        return EntityMeta(type=type_, content=content)

    @classmethod
    def __from_entity_meta__(cls, meta: EntityMeta) -> Self:
        data = json.loads(meta["content"])
        ctx_data = data["ctx"]
        children_data = data["children"]
        result = cls(**ctx_data)
        children = []
        for child in children_data:
            children.append(from_entity_meta(child))
        return result.with_children(*children)


class PromptAbleObj(ABC):
    """
    拥有 __prompt__ 方法的类.
    这里只是一个示范, 并不需要真正继承这个类, 只需要有 __prompt__ 方法或属性.
    """

    @abstractmethod
    def __prompt__(self) -> str:
        pass


class PromptAbleProtocol(Protocol):
    @abstractmethod
    def __prompt__(self) -> str:
        pass


class PromptAbleClass(ABC):

    @classmethod
    @abstractmethod
    def __class_prompt__(cls) -> str:
        pass


class PromptAbleClassProtocol(Protocol):

    @classmethod
    @abstractmethod
    def __class_prompt__(cls) -> str:
        pass


PromptAble = Union[PromptAbleClass, PromptAbleObj, PromptAbleProtocol, PromptAbleClassProtocol]
