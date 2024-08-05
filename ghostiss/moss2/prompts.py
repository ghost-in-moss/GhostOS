from typing import Any, Optional, Union, Type, Callable, Dict, Tuple, Iterable
from abc import ABC, abstractmethod
from ghostiss.moss2.utils import (
    get_str_from_func_or_attr, is_typing,
    is_code_same_as_print,
    escape_string_quotes,
)
from ghostiss.moss2.reflection import Reflection
from types import ModuleType
import inspect

"""
将上下文引用的 变量/方法/类型 反射出 Prompt 的机制. 
主要解决一个问题, 如何让一个属性能够被大模型所理解. 

本质上有三种机制: 
+ 类: 展示折叠的, 或者全部的源码. 
+ 方法: 展示折叠的, 或者全部的源码. 
+ 属性: 展示属性的 typehint. 又有几种做法: 
    - 赋值: 类似 `x:int=123` 的形式展示. 
    - 类型: 没有赋值, 只有 `x: foo` 的方式展示. 
    - 字符串类型: 用字符串的方式来描述类型. 比如 `x: "<foo.Bar>"`. 其类型说明是打印结果. 
    - doc: 在 python 的规范里, 属性可以在其下追加字符串作为它的说明. 

预计有以下几种机制: 

1. 在代码里手写注释或者字符串说明. 
2. 如果变量拥有 __prompt__ 属性, 通过它 (可以是方法或字符串) 生成 prompt. 
3. 属性直接是一个 Reflection 实例, 会将它的 value() 替换到上下文里, 而使用它的 prompt. 
"""

PROMPT_MAGIC_ATTR = "__prompt__"
"""系统假设目标拥有 prompt 能力, 通过这个属性名来判断."""

ATTR_PROMPT_MAGIC_ATTR = "__attr_prompts__"

PromptFn = Callable[[], str]
"""生成 Prompt 的方法. """

Numeric = Union[int, float]

AttrPrompts = Iterable[Tuple[str, str]]
"""
描述多个属性的代码, 作为 prompt 提供给 LLM. 
每个元素代表一个属性. 
元素的值为 Tuple[name, prompt] 
name 是为了去重, prompt 应该就是原有的 prompt. 

如果 attr_name 存在, 使用 f"{name}{prompt}" 格式化, 预计结构是:`name[: typehint] = value[\n\"""doc\"""]`
如果 attr_name 不存在, 则直接使用 prompt. 

多条 prompt 用 "\n\n".join(prompts) 的方式拼接. 
"""


def reflect_locals(__name__: str, local_values: Dict[str, Any]) -> AttrPrompts:
    pass


def join_prompt_lines(*prompts: Optional[str]) -> str:
    result = []
    for prompt in prompts:
        if prompt:
            result.append(prompt)
    return '\n'.join(result)


def get_prompt(target: Any) -> Optional[str]:
    if inspect.ismodule(target):
        pass
    elif inspect.isclass(target):
        pass
    elif inspect.isfunction(target):
        pass
    elif inspect.ismethod(target):
        pass


def assign_prompt(typehint: Optional[Any], assigment: Optional[Any]) -> str:
    """
    拼装一个赋值的 Prompt.
    :param typehint: 拼装类型描述, 如果是字符串直接展示, 否则会包在双引号里.
    :param assigment:
    :return:
    """
    if isinstance(typehint, str):
        typehint_str = f': {typehint}'
    else:
        s = escape_string_quotes(str(typehint), '"')
        typehint_str = f': "{s}"'
    assigment_str = ""
    if isinstance(assigment, str):
        s = escape_string_quotes(str(typehint), '"')
        assigment_str = f' = "{s}"'
    elif is_code_same_as_print(assigment):
        assigment_str = f' = {assigment}'
    return f"{typehint_str}{assigment_str}"


def compile_attr_prompts(attr_prompts: AttrPrompts) -> str:
    """
    将 Attr prompt 进行合并.
    :param attr_prompts:
    :return: prompt in real python code pattern
    """
    prompt_lines = []
    for prompt, name in attr_prompts:
        if not prompt:
            # prompt 为空就跳过.
            continue
        elif name:
            # 这里判断 prompt 的结构是 `[: typehint] = value[\n"""doc"""]`
            prompt_lines.append(f"{name}{prompt}")
        else:
            # 使用注释 + 描述的办法.
            prompt_lines.append(prompt)
    return join_prompt_lines(*prompt_lines)


def set_prompt(value: Any, prompt: Union[str, PromptFn]) -> Any:
    """
    尝试给一个目标对象赋予 __prompt__
    :param value: Union[Type, object, Dict] 可以是类, 对象, 字典.
    :param prompt: 可以是字符串或者一个 Prompter
    :return: value self
    """
    if isinstance(value, Dict):
        value[PROMPT_MAGIC_ATTR] = prompt() if isinstance(prompt, Callable) else prompt
    elif inspect.isclass(value) or inspect.isfunction(value) or inspect.ismethod(value):
        setattr(value, PROMPT_MAGIC_ATTR, prompt)
    else:
        raise TypeError('only class/method/function/dict allowed to add __prompt__ attr')
    return value


def could_add__prompt__(value: Any) -> bool:
    return inspect.isclass(value) or inspect.isfunction(value) or inspect.ismethod(value)


# def get_prompt(value: Any) -> Optional[str]:
#     """
#     从一个目标对象中尝试获取它预定义的 prompt.
#     """
#     if isinstance(value, Dict):
#         return value.get(PROMPT_MAGIC_ATTR, None)
#     elif isinstance(value, PromptAble):
#         return value.__prompt__()
#     elif hasattr(value, PROMPT_MAGIC_ATTR):
#         prompt = getattr(value, PROMPT_MAGIC_ATTR)
#         if isinstance(prompt, Callable):
#             return prompt()
#         return prompt
#     return None


def get_prompt(value: Any) -> Optional[str]:
    if value is None:
        # if not name:
        #     raise ValueError("name cannot be None if value is None")
        # return f"{name} = None"
        pass
    # 如果是一个 Prompter 对象, 则直接生成 prompt.
    elif isinstance(value, Reflection):
        pass
    # 如果包含 __prompt__ 属性, 则预期它是一个字符串, 或者生成一个字符串.
    elif hasattr(value, PROMPT_MAGIC_ATTR):
        # prompter = getattr(value, PROMPT_MAGIC_ATTR)
        # return prompter(name)
        pass
    elif inspect.ismodule(value):
        # return prompt_module(value, name)
        pass
    elif isinstance(value, Numeric) or isinstance(value, bool):
        # return f"{name} = {value}"
        pass
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
