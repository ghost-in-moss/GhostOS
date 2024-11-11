from __future__ import annotations

import inspect
from typing import (
    List, Self, Union, Callable, Any, Protocol, Optional, Dict,
)
from abc import ABC, abstractmethod
from types import ModuleType
from ghostos.container import Container
from ghostos.helpers import generate_import_path
import json

from pydantic import BaseModel, Field
from .entity import EntityClass, EntityMeta, from_entity_meta, to_entity_meta

__all__ = [
    'get_defined_prompt',
    'set_prompter', 'set_class_prompter',
    'Prompter',
    'TextPrmt',
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

    priority: int = Field(default=0, description='Priority of this prompter.')

    __children__: Optional[List[Prompter]] = None
    """ children is fractal sub context nodes"""

    __self_prompt__: Optional[str] = None

    def with_children(self, *children: Prompter) -> Prompter:
        if self.__children__ is None:
            self.__children__ = []
        children = list(children)
        if len(children) > 0:
            self.__children__.extend(children)
        return self

    @abstractmethod
    def self_prompt(self, container: Container) -> str:
        """
        generate prompt by self, without children
        :param container:
        :return:
        """
        pass

    @abstractmethod
    def get_title(self) -> str:
        """
        the title of the prompt
        """
        pass

    def get_priority(self) -> int:
        return 0

    def get_prompt(self, container: Container, depth: int = 0) -> str:
        """
        get prompt with container which provides libraries to generate prompt
        :param container:
        :param depth:
        :return:
        """
        if self.__self_prompt__ is not None:
            return self.__self_prompt__

        title = self.get_title()
        if title:
            title = '#' * (depth + 1) + ' ' + title

        self_prompt = self.self_prompt(container)
        prompts = []
        if self_prompt:
            prompts.append(self_prompt)

        if self.__children__ is not None:
            for child in self.__children__:
                child_prompt = child.get_prompt(container, depth=depth + 1)
                if child_prompt:
                    prompts.append(child_prompt)
        # empty prompts
        if not prompts:
            return ""

        # generate output prompt
        prompts.insert(0, title)
        output = ""
        for paragraph in prompts:
            paragraph = paragraph.strip()
            if paragraph:
                output += "\n\n" + paragraph
        self.__self_prompt__ = output.strip()
        return self.__self_prompt__

    def __to_entity_meta__(self) -> EntityMeta:
        type_ = generate_import_path(self.__class__)
        ctx_data = self.model_dump(exclude_defaults=True)
        children_data = []
        if self.__children__ is not None:
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

    def flatten(self, index: str = "") -> Dict[str, Self]:
        if not index:
            index = "0"
        result = {index: self}
        idx = 0
        for child in self.__children__:
            sub_index = index + "." + str(idx)
            sub_flatten = child.flatten(sub_index)
            for key in sub_flatten:
                result[key] = sub_flatten[key]
        return result


class TextPrmt(Prompter):
    title: str = ""
    content: str = ""

    def self_prompt(self, container: Container) -> str:
        return self.content

    def get_title(self) -> str:
        return self.title


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
