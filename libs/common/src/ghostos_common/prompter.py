from __future__ import annotations

import inspect
from typing import (
    List, Union, Callable, Any, Protocol, Optional, Dict, TypeVar, Type, Generic, Iterable,
)
from typing_extensions import Self
from abc import ABC, abstractmethod
from types import ModuleType
from ghostos_container import Container
from ghostos_common.helpers import generate_import_path, import_class_from_path, import_from_path
from pydantic import BaseModel, Field
from ghostos_common.entity import EntityMeta, from_entity_meta, to_entity_meta

import json

__all__ = [

    # -- prompt object model -- #
    'PromptObjectModel', 'POM', 'BasePOM',
    'DataPOM', 'DataPOMDriver',
    'TextPOM',
    'InspectPOM',

    # --- get value prompt --- #
    'get_defined_prompt',
    'set_prompt', 'set_class_prompt',
    'PromptAbleObj', 'PromptAbleClass',
    'PromptAbleProtocol',
    'PromptAbleClassProtocol',
    'PromptAble',
]


def get_defined_prompt(value: Any, container: Optional[Container] = None) -> Union[str, None]:
    attr = get_defined_prompt_attr(value, container)
    if attr is None:
        return None
    if isinstance(attr, str):
        return attr
    return attr()


def get_defined_prompt_attr(value: Any, container: Optional[Container] = None) -> Union[None, str, Callable[[], str]]:
    if value is None:
        return None
    elif isinstance(value, PromptAbleObj):
        return value.__prompt__
    elif isinstance(value, PromptObjectModel) and container is not None:
        return value.get_prompt(container)

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


def set_prompt(obj: Any, prompter: Union[Callable[[], str], str], force: bool = False) -> None:
    if force or not hasattr(obj, '__prompt__'):
        setattr(obj, '__prompt__', prompter)


def set_class_prompt(cls: type, prompter: Union[Callable[[], str], str], force: bool = False) -> None:
    if hasattr(cls, '__class__prompt__'):
        fn = getattr(cls, '__class_prompt__')
        cls_name = generate_import_path(cls)
        if force or fn.__class_name__ != cls_name:
            pass
        else:
            return
    prompter.__class_name__ = generate_import_path(cls)
    setattr(cls, '__class_prompt__', prompter)


# ---- prompter ---- #

class PromptObjectModel(ABC):
    """
    tree like object model to generate a prompt.
    a POM is a node of the tree.
    the tree generate prompt from all the nodes.
    """

    __children__: Optional[List[PromptObjectModel]] = None
    """ children is fractal sub context nodes"""

    __named_children__: Optional[Dict[str, PromptObjectModel]] = None
    """ children with unique names"""

    def with_children(self, *children: PromptObjectModel, **slots_children: PromptObjectModel) -> Self:
        children = list(children)
        if len(children) > 0:
            for child in children:
                if child is None:
                    continue
                self.add_child(child)

        for key, value in slots_children.items():
            self.add_named_child(key, value)
        return self

    def add_child(self, *prompters: PromptObjectModel) -> Self:
        if self.__children__ is None:
            self.__children__ = []
        for prompter in prompters:
            self.__children__.append(prompter)
        return self

    def add_named_child(self, key: str, value: PromptObjectModel) -> Self:
        if self.__named_children__ is None:
            self.__named_children__ = {}
        self.__named_children__[key] = value
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

    def list_children(self) -> Iterable[PromptObjectModel]:
        if self.__named_children__ is not None:
            for child in self.__named_children__.values():
                yield child

        if self.__children__ is not None:
            for child in self.__children__:
                yield child

    def get_prompt(self, container: Container, depth: int = 0) -> str:
        """
        get prompt with container which provides libraries to generate prompt
        :param container:
        :param depth:
        :return:
        """

        title = self.get_title()
        depth = depth
        if title:
            title = '#' * (depth + 1) + ' ' + title
            depth = depth + 1

        self_prompt = self.self_prompt(container)
        prompts = []
        if self_prompt:
            prompts.append(self_prompt)

        for child in self.list_children():
            child_prompt = child.get_prompt(container, depth=depth)
            if child_prompt:
                prompts.append(child_prompt)

        # empty prompts
        if not prompts:
            return ""

        # generate output prompt
        if title:
            prompts.insert(0, title)
        output = ""
        for paragraph in prompts:
            paragraph = paragraph.strip()
            if paragraph:
                output += "\n\n" + paragraph

        return output.strip()

    def flatten(self, index: str = "") -> Dict[str, Self]:
        if not index:
            index = "0"
        result = {index: self}
        idx = 0
        for child in self.list_children():
            if not child:
                continue
            sub_index = index + "." + str(idx)
            sub_flatten = child.flatten(sub_index)
            for key in sub_flatten:
                result[key] = sub_flatten[key]
        return result


class BasePOM(BaseModel, PromptObjectModel, ABC):

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


POM = PromptObjectModel
"""alias of the PromptObjectModel"""


class DataPOM(PromptObjectModel, ABC):
    """
    data pom separate DataPOMDriver from the data.
    want to hide methods to whom look at its source.
    """
    __driver__: Optional[Type[DataPOMDriver]] = None

    def get_driver(self) -> DataPOMDriver:
        driver = self.__driver__
        if driver is None:
            driver_path = generate_import_path(self.__class__) + "Driver"
            driver = import_class_from_path(driver_path, DataPOMDriver)
        return driver(self)

    def self_prompt(self, container: Container) -> str:
        """
        generate prompt from model values with libraries that container provides.
        :param container: IoC container provides library implementation.
        :return: natural language prompt
        """
        return self.get_driver().self_prompt(container)

    def get_title(self) -> str:
        return self.get_driver().get_title()


D = TypeVar("D", bound=DataPOM)


class DataPOMDriver(Generic[D], ABC):

    def __init__(self, data: D):
        self.data = data

    @abstractmethod
    def self_prompt(self, container: Container) -> str:
        """
        generate prompt from model values with libraries that container provides.
        :param container: IoC container provides library implementation.
        :return: natural language prompt
        """
        pass

    @abstractmethod
    def get_title(self) -> str:
        pass


class TextPOM(BasePOM):
    """
    simplest text Project Object Model.
    """
    title: str = ""
    content: str = ""

    def self_prompt(self, container: Container) -> str:
        return self.content

    def get_title(self) -> str:
        return self.title


class InspectPOM(BasePOM, DataPOM):
    """
    test only object.
    """

    title: str = Field(
        default="Code Inspection",
        description="The title of the inspect prompt.",
    )
    source_target: List[str] = Field(
        default_factory=list,
        description="Inspect source code of these targets. ",
    )

    def inspect_source(self, target: Union[type, Callable, str]) -> Self:
        if not isinstance(target, str):
            target = generate_import_path(target)
        self.source_target.append(target)
        return self


class InspectPOMDriver(DataPOMDriver[InspectPOM]):

    def self_prompt(self, container: Container) -> str:
        prompts = {}
        for target in self.data.source_target:
            got = import_from_path(target)
            source = inspect.getsource(got)
            prompts[target] = source

        result = ""
        for target, source in prompts.items():
            source = source.strip()
            if not source:
                continue
            result += f"""

source code of `{target}`:
```python
{source}
```
"""
        return result.strip()

    def get_title(self) -> str:
        pass


# ---- prompt-able ---- #

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
