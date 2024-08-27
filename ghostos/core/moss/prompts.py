from typing import Any, Optional, Union, Callable, Dict, Tuple, Iterable, Set, Type
from types import ModuleType
from ghostos.core.moss.utils import (
    unwrap_str,
    is_typing,
    is_code_same_as_print,
    escape_string_quotes,
    get_modulename,
    get_callable_definition,
    add_source_indent,
)
from ghostos.abc import PromptAble, PromptAbleClass
from ghostos.helpers import generate_import_path
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
"""

PROMPT_MAGIC_ATTR = "__prompt__"
"""通过这个属性名来判断一个实例 (module/function/instance of class) 是否有预定义的 prompt. """

CLASS_PROMPT_MAGIC_ATTR = "__class__prompt__"

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


def reflect_module_locals(
        modulename: str,
        local_values: Dict[str, Any],
        *,
        includes: Optional[Set[str]] = None,
        excludes: Optional[Set[str]] = None,
        includes_module_prefixes: Optional[Set[str]] = None,
        excludes_module_prefixes: Optional[Set[str]] = None,
        _cls: bool = True,
        _typing: bool = True,
        _func: bool = True,
        _module: bool = False,
        _prompter: bool = True,
) -> AttrPrompts:
    """
    MOSS 系统自带的反射方法, 对一个module 的本地变量做最小化的反射展示.
    基本原理:
    1. 当前模块变量:
       - 当前模块的变量默认不展示, 因为本地变量的 prompt 可以直接写在代码里.
       - 如果定义了 __prompt__ 方法, 则会展示出来.
    2. 不反射任何 `_` 开头的本地变量.
    3. 不反射 builtin 类型.
    4. 如果目标是 module
        - 包含 __prompt__ 方法时嵌套展示
        - 否则不展示. 避免递归问题.
    5. 如果目标是 function
        - 包含 __prompt__ 方法时使用它生成,
        - 否则返回 function 的 definition + doc
    6. 如果目标是 class
        - 包含 __class_prompt__ 方法时, 用它生成.
        - __is_abstract__ 的 class, 直接返回源码.
    7. 如果目标是 typing
        - 如果目标就是 typing 库, 则不展示.
        - 否则用字符串形式展示.
    8. 如果目标是其它 attr
        _ 只有包含 prompt 方法时才展示.

    :param modulename: 当前模块名. 所有当前模块的变量默认不展示.
    :param local_values: 传入的上下文变量.
    :param includes: if given, only prompt the attrs that name in it
    :param excludes: if given, any attr that name in it will not be prompted
    :param includes_module_prefixes: if given, the other module's value will only be prompted if the module match prefix
    :param excludes_module_prefixes: if given, the other module's value will not be prompted if the module match prefix
    :param _cls: 是否允许反射类.
    :param _module: 是否允许反射模块.
    :param _typing: 是否允许反射 typing
    :param _func: 是否允许反射 function.
    :param _prompter: 拥有 __prompt__ 的其它类型.
    """
    for name, value in local_values.items():
        try:
            prompt = reflect_module_attr(
                name, value, modulename, includes, excludes, includes_module_prefixes, excludes_module_prefixes,
                _cls, _module, _func, _prompter,
            )
        except Exception as e:
            raise RuntimeError(f"failed to reflect local value {name!r}: {e}")
        if prompt is not None:
            yield name, prompt


def reflect_module_attr(
        name: str,
        value: Any,
        current_module: Optional[str] = None,
        includes: Optional[Set[str]] = None,
        excludes: Optional[Set[str]] = None,
        includes_module_prefixes: Optional[Set[str]] = None,
        excludes_module_prefixes: Optional[Set[str]] = None,
        _cls: bool = True,
        _typing: bool = True,
        _func: bool = True,
        _module: bool = False,
        _prompter: bool = True,
) -> Optional[str]:
    """
    反射其中的一个值.
    """
    # 名字相关的过滤逻辑.
    if excludes and name in excludes:
        return None
    if includes is not None and name not in includes:
        return None
    if name.startswith('_') and not (includes and name in includes):
        # 私有变量不展示.
        return None
    if inspect.isbuiltin(value):
        # 系统内置的, 都不展示.
        return None

    # module 相关的过滤逻辑.
    value_modulename = get_modulename(value)
    if value_modulename is None:
        return None
    elif value_modulename == current_module:
        return None

    if excludes_module_prefixes:
        for prefix in excludes_module_prefixes:
            if value_modulename.startswith(prefix):
                return None

    elif includes_module_prefixes:
        has_prefix = False
        for prefix in includes_module_prefixes:
            if value_modulename.startswith(prefix):
                has_prefix = True
                break
        if not has_prefix:
            return None
    return default_reflect_local_value_prompt(
        name, value,
        _cls=_cls, _typing=_typing, _module=_module, _func=_func, _prompter=_prompter,
    )


def default_reflect_local_value_prompt(
        name: str,
        value: Any,
        _cls: bool = True,
        _module: bool = True,
        _typing: bool = True,
        _func: bool = True,
        _prompter: bool = True,
) -> Optional[str]:
    """
    默认的反射方法, 用来反射当前上下文(module) 里的某个变量, 生成上下文相关的 prompt (assignment or definition).
    :param name: 变量名.
    :param value: 变量值
    :param _cls: 是否允许反射类.
    :param _module: 是否允许反射模块.
    :param _typing: 是否允许反射 typing
    :param _func: 是否允许反射 function.
    :param _prompter: 其它类型.
    :return:
    """
    # 如果是 module 类型.
    if is_typing(value):
        if not _typing:
            return None
        if value.__module__ == "typing":
            if value.__name__ in _typing.__dict__ and _typing.__dict__[value.__name__] is value:
                return None
        return f"{name} = {value}"

    elif inspect.isclass(value):
        if not _cls:
            return None
        # class 类型.
        prompt = get_class_magic_prompt(value)
        if prompt is not None:
            return prompt
        if inspect.isabstract(value):
            source = inspect.getsource(value)
            return source

    elif inspect.isfunction(value) or inspect.ismethod(value):
        if not _func:
            return None
        # 方法类型.
        prompt = get_magic_prompt(value)
        if prompt is not None:
            return prompt
        # 默认都给方法展示 definition.
        return get_callable_definition(value, name)
    elif inspect.ismodule(value):
        if not _module:
            return None
        # 只有包含 __prompt__ 的库才有展示.
        prompt = get_magic_prompt(value)
        if prompt:
            parsed = escape_string_quotes(prompt, '"""')
            # 增加缩进.
            parsed = add_source_indent(parsed, indent=4)
            return f'''
# information of `{name}` (module `{value.__name__}`) :
"""
{parsed}
"""
# information of `{name}` over.
'''

    else:
        if not _prompter:
            return None
        # attr, 也可能是 module.
        prompt = get_magic_prompt(value)
        if prompt:
            parsed = escape_string_quotes(prompt, '"""')
            return f'''
# value of `{name}`:
"""
{parsed}
"""
# value of `{name}` over.
'''
    return None


def get_prompt(value: Any) -> Optional[str]:
    if inspect.isclass(value):
        return get_class_magic_prompt(value)
    return get_magic_prompt(value)


def get_magic_prompt(value: Any) -> Optional[str]:
    """
    不做类型校验, 直接返回 PROMPT_MAGIC_ATTR 生成 prompt 的结果.
    :param value: 合理类型是 module, function, method, instance of class
    """
    if isinstance(value, PromptAble):
        return value.__prompt__()
    fn = getattr(value, PROMPT_MAGIC_ATTR, None)
    return unwrap_str(fn) if fn is not None else None


def get_class_magic_prompt(value: Any) -> Optional[str]:
    """
    不做类型校验, 直接返回 CLASS_PROMPT_MAGIC_ATTR 生成 prompt 的结果.
    :param value: 合理的类型是 class.
    """
    if issubclass(value, PromptAbleClass):
        return value.__class_prompt__()
    fn = getattr(value, CLASS_PROMPT_MAGIC_ATTR, None)
    return unwrap_str(fn) if fn is not None else None


def join_prompt_lines(*prompts: Optional[str]) -> str:
    """
    将多个可能为空的 prompt 合并成一个 python 代码风格的 prompt.
    """
    result = []
    for prompt in prompts:
        line = prompt.rstrip()
        if line:
            result.append(prompt)
    return '\n\n\n'.join(result)


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


def compile_attr_prompts(module: ModuleType, attr_prompts: AttrPrompts) -> str:
    """
    将 Attr prompt 进行合并.
    :param module: 用来做类型判断, 如何处理 name.
    :param attr_prompts:
    :return: prompt in real python code pattern
    """
    prompt_lines = []
    local_values = module.__dict__
    local_module = module.__name__
    for name, prompt in attr_prompts:
        line = prompt.strip()
        if not line:
            # 空值跳过.
            continue
        value = local_values.get(name, None)
        if value is None:
            # 不在当前的变量里, 直接加入上下文.
            prompt_lines.append(line)
        elif getattr(value, "__module__", None) == local_module:
            prompt_lines.append(line)
        elif inspect.isclass(value):
            # 考虑到重命名.
            if name != value.__name__:
                line = xml_wrap_code(line, "class", name=name, path=value.__module__ + ':' + value.__qualname__)
            prompt_lines.append(line)
        elif inspect.isfunction(value):
            # 考虑到重命名.
            if name != value.__name__:
                line = xml_wrap_code(line, "func", name=name, path=value.__module__ + ':' + value.__qualname__)
            prompt_lines.append(line)
        elif inspect.ismodule(value):
            # 考虑到重命名.
            line = xml_wrap_code(line, "module", name=name, module=value.__name__)
            prompt_lines.append(line)
        else:
            # 使用注释 + 描述的办法.
            prompt_lines.append(f"# value '{name}':\n{line}")
    return join_prompt_lines(*prompt_lines)


def xml_wrap_code(value: str, mark: str, **kwargs: str) -> str:
    kwargs_str = ""
    if kwargs:
        lines = [f"{name}='{arg}'" for name, arg in kwargs.items()]
        kwargs_str = ' ' + ' '.join(lines)
    start = f"# <{mark}{kwargs_str}>"
    end = f"# </{mark}>"
    return "\n".join([start, value, end])


def set_prompter(value: Any, prompter: Union[PromptFn, str], force: bool = False) -> None:
    if not force and hasattr(value, PROMPT_MAGIC_ATTR):
        return
    setattr(value, PROMPT_MAGIC_ATTR, prompter)


def set_class_prompter(value: Type, class_prompter: Union[PromptFn, str], force: bool = False) -> None:
    if not inspect.isclass(value):
        raise TypeError(f'`value` should be a class, not {type(value)}')
    class_name = generate_import_path(value)
    if hasattr(value, CLASS_PROMPT_MAGIC_ATTR):
        method = getattr(value, CLASS_PROMPT_MAGIC_ATTR)
        if method is not None and isinstance(method, Callable):
            cls_name = getattr(method, '__prompter_class__', None)
            # 同一个类已经有 prompt 的情况, 必须加 force 参数才能修改原有的.
            if cls_name == class_name and not force:
                return
    if isinstance(class_prompter, Callable):
        # 会给 prompter 方法添加 __prompter_class__ 用来做归属判断.
        # todo: 有没有更好的解决办法?
        class_prompter.__prompter_class__ = class_name
    setattr(value, CLASS_PROMPT_MAGIC_ATTR, class_prompter)
