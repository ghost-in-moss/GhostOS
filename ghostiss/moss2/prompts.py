from typing import Any, Optional, Union, Type, Callable
from abc import ABC, abstractmethod
from ghostiss.moss2.utils import (
    get_str_from_func_or_attr, is_typing,
)
from ghostiss.moss2.reflection import Reflection
from types import ModuleType
import inspect

"""
将上下文引用的 变量/方法/类型 反射出 Prompt 的机制. 
主要解决两个问题: 
1. 代码中 from ... import ... 拿到的变量, 它的 prompt 是什么. 
2. 当前文件有一些代码, 并不希望被大模型看到. 它们如何反射. 

预计有以下几种机制: 

1. 在代码里手写注释或者字符串说明. 
2. 如果变量拥有 __prompt__ 属性, 通过它 (可以是方法或字符串) 生成 prompt. 
3. 属性直接是一个 Reflection 实例, 会将它的 value() 替换到上下文里, 而使用它的 prompt. 
"""

MOSS_PROMPTER_MAGIC_ATTR = "__prompt__"
MossPrompterAttr = Callable[[], str]
MossPrompterDecorator = Callable[[Any], Any]
Numeric = Union[int, float]


def prompt(
        value: Any,
        name: str
) -> Optional[str]:
    if value is None:
        if not name:
            raise ValueError("name cannot be None if value is None")
        return f"{name} = None"
    # 如果是一个 Prompter 对象, 则直接生成 prompt.
    elif isinstance(value, Reflection):
        return value.prompt()
    # 如果包含 __prompt__ 属性, 则预期它是一个字符串, 或者生成一个字符串.
    elif hasattr(value, MOSS_PROMPTER_MAGIC_ATTR):
        prompter = getattr(value, MOSS_PROMPTER_MAGIC_ATTR)
        return prompter(name)
    elif inspect.ismodule(value):
        return prompt_module(value, name)
    elif isinstance(value, Numeric) or isinstance(value, bool):
        return f"{name} = {value}"
    elif is_typing(value):
        # todo
        pass
    elif inspect.isclass(value):
        # todo
        pass
    elif isinstance(value, Callable):
        # todo
        pass
    else:
        # todo
        pass


def prompt_module(module: ModuleType) -> Optional[str]:
    pass


class Prompter(ABC):
    """
    reflect a value to moss context.
    """

    @abstractmethod
    def value(self) -> str:
        pass

    @abstractmethod
    def generate_prompt(self, name: Optional[str] = None) -> str:
        pass


class AttrPrompter(Prompter, ABC):
    pass


class CallablePrompter(Prompter, ABC):
    pass


class TypePrompter(Prompter, ABC):
    pass


class Attr(AttrPrompter):
    pass


class DictAttr(AttrPrompter):
    pass


class Typing(AttrPrompter):
    pass


class Interface(TypePrompter):
    pass


class ClassStub(TypePrompter):
    pass
