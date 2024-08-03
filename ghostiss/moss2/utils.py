import inspect
import re
from typing import Any, Dict, Callable, Optional, List, Iterable, TypedDict, Union, Type, is_typeddict, Tuple
from abc import ABC, abstractmethod
from pydantic import BaseModel
from ghostiss.entity import EntityClass
from ghostiss.abc import Identifiable, Descriptive

__all__ = [

    'BasicTypes', 'ModelType', 'ModelObject',
    'Reflection', 'IterableReflection',
    'TypeReflection', 'ValueReflection', 'CallerReflection', 'Importing',

    'Typing',
    'Attr', 'Method',
    'Class', 'SourceCode',
    'ClassPrompter', 'Interface', 'ClassSign',
    'Locals', 'BuildObject',

    'reflect', 'reflects',

    'is_typing', 'is_builtin', 'is_classmethod',
    'is_model_class', 'get_model_object_meta', 'is_model_instance', 'new_model_instance',
    'parse_comments',
    'parse_doc_string', 'parse_doc_string_with_quotes',
    'strip_source_indent', 'add_source_indent', 'make_class_prompt',
    'is_callable', 'is_public_callable', 'parse_callable_to_method_def',
    'get_typehint_string', 'get_default_typehint', 'get_import_comment', 'get_extends_comment',
    'get_class_def_from_source',
    'count_source_indent',
    'replace_class_def_name',
    'get_calling_modulename',
]


def reflect(
        *,
        var: Any,
        name: Optional[str] = None,
) -> Optional[Reflection]:
    """
    reflect any variable to Reflection
    """
    if isinstance(var, Reflection):
        if name:
            var = var.update(name=name)
        return var

    elif is_builtin(var):
        return Importing(value=var)

    elif is_typing(var):
        if not name:
            raise ValueError('Name must be a non-empty string for typing')
        return Typing(name=name, typing=var)
    elif inspect.isclass(var):
        return SourceCode(cls=var, name=name)
    elif isinstance(var, Callable):
        return Method(caller=var, name=name)
    elif not name:
        raise ValueError(f'Name must be a non-empty string for Attr type {type(var)}, value {var}')

    return Attr(name=name, value=var)


def reflects(*args, **kwargs) -> Iterable[Reflection]:
    """
    reflect any variable to Reflection
    """
    for arg in args:
        if isinstance(arg, IterableReflection):
            for item in arg.iterate():
                yield item
            continue

        r = reflect(var=arg)
        if r is not None:
            yield r

    for k, v in kwargs.items():
        if isinstance(v, IterableReflection):
            for item in v.iterate():
                yield item
            continue
        r = reflect(var=v, name=k)
        if r is not None:
            yield r


def get_import_comment(module: Optional[str], module_spec: Optional[str], alias: Optional[str]) -> Optional[str]:
    if module:
        if module_spec:
            if alias and alias != module_spec:
                return f"# from {module} import {module_spec} as {alias}"
            else:
                return f"# from {module} import {module_spec}"
        elif alias and not module.endswith(alias):
            return f"# import {module} as {alias}"
        else:
            return f"# import {module}"
    return None


def get_extends_comment(extends: Optional[List[Any]]) -> Optional[str]:
    if not extends:
        return None
    result = []
    for imp in extends:
        if not imp:
            continue
        elif isinstance(imp, str):
            result.append(imp)
        else:
            result.append('"' + str(imp) + '"')
    return "# extends " + ", ".join(result)


def join_prompt_lines(*prompts: Optional[str]) -> str:
    result = []
    for prompt in prompts:
        if prompt:
            result.append(prompt)
    return '\n'.join(result)


def get_typehint_string(typehint: Optional[Any]) -> str:
    if not typehint:
        return ""
    if isinstance(typehint, str):
        if typehint.lstrip().startswith(":"):
            return typehint
        return ": " + typehint
    if is_typing(typehint):
        return ": " + str(typehint)
    else:
        return ': "' + str(typehint) + '"'


def parse_doc_string(doc: Optional[str], inline: bool = True, quote: str = '"""') -> str:
    if not doc:
        return ""
    gap = "" if inline else "\n"
    doc = strip_source_indent(doc)
    doc = parse_doc_string_with_quotes(doc, quote=quote)
    return quote + gap + doc + gap + quote


def parse_comments(comment: Optional[str]) -> str:
    if not comment:
        return ""
    comments = comment.split('\n')
    result = []
    for c in comments:
        c = c.strip()
        if not c.startswith('#'):
            c = '# ' + c
        result.append(c)
    return '\n'.join(result)


def make_class_prompt(
        *,
        source: str,
        name: str,
        doc: Optional[str] = None,
        attrs: Optional[Iterable[str]] = None,
) -> str:
    source = strip_source_indent(source)
    class_def = get_class_def_from_source(source)
    class_def = replace_class_def_name(class_def, name)
    if doc:
        doc = parse_doc_string(doc, inline=False, quote='"""')
    if doc:
        class_def += "\n" + add_source_indent(doc, 4)
    blocks = []
    if attrs:
        for attr in attrs:
            blocks.append(attr)
    if len(blocks) == 0:
        class_def += "\n" + add_source_indent("pass", 4)
        return class_def

    i = 0
    for block in blocks:
        _block = add_source_indent(block, 4)
        exp = "\n\n" if i > 0 else "\n"
        class_def += exp + _block
        i += 1
    return class_def


def replace_class_def_name(class_def: str, new_name: str) -> str:
    found = re.search(r'class\s+\w+[(:]', class_def)
    if not found:
        raise ValueError(f"Could not find class definition in {class_def}")
    found_str = found.group(0)
    found_str = found_str[:len(found_str) - 1]
    replace = f"class {new_name}"
    return class_def.replace(found_str, replace, 1)


def get_class_def_from_source(source: str) -> str:
    result = []
    source = strip_source_indent(source)
    source = source.strip()
    lines = source.split('\n')
    found_class = False
    for line in lines:
        line = line.rstrip()
        result.append(line)
        if line.startswith('class '):
            found_class = True
        unmarked = line.split('#')[0].rstrip()
        if found_class and unmarked.endswith(':'):
            break
    return '\n'.join(result)


def is_typing(value: Any) -> bool:
    if hasattr(value, "__module__"):
        return getattr(value, "__module__") == "typing"
    return False


def is_builtin(value: Any) -> bool:
    if inspect.isbuiltin(value):
        return True
    if not inspect.isclass(value):
        return False
    return value.__module__ == "__builtin__"


def is_classmethod(func: Any) -> bool:
    """
    判断一个变量是不是一个 @classmethod.
    code by moonshot
    """
    if not isinstance(func, Callable):
        return False
    if not inspect.ismethod(func):
        return False
    if not hasattr(func, '__self__'):
        return False
    self = getattr(func, '__self__', None)
    return self is not None and isinstance(self, type)


def get_str_from_func_or_attr(value: Any) -> Optional[str]:
    if isinstance(value, Callable):
        return value()
    try:
        return str(value)
    except AttributeError:
        return None


def parse_callable_to_method_def(
        caller: Callable,
        alias: Optional[str] = None,
        doc: Optional[str] = None,
) -> str:
    """
    将一个 callable 对象的源码剥离方法和描述.
    """
    if doc:
        doc = doc.strip()
    if not inspect.isfunction(caller) and not inspect.ismethod(caller):
        if not inspect.isclass(caller) and isinstance(caller, Callable) and hasattr(caller, '__call__'):
            if not alias:
                alias = type(caller).__name__
            if not doc:
                doc = inspect.getdoc(caller)
            caller = getattr(caller, '__call__')
        else:
            raise TypeError(f'"{caller}" is not function or method')

    source_code = inspect.getsource(caller)
    stripped_source = strip_source_indent(source_code)
    source_lines = stripped_source.split('\n')
    definition = []

    # 获取 method def
    for line in source_lines:
        # if line.startswith('def ') or len(definition) > 0:
        line = line.rstrip()
        if line == "@abstractmethod":
            continue
        definition.append(line)
        code_line = line.split('#')[0]
        if code_line.rstrip().endswith(':'):
            break
    defined = '\n'.join(definition).strip()
    if alias:
        found = re.search(r'def\s+(\w+)\(', defined)
        if found:
            defined = defined.replace(found.group(0), "def {name}(".format(name=alias), 1)
    indent_str = ' ' * 4
    if doc is None:
        doc = caller.__doc__ or ""
    if doc:
        doc = parse_doc_string(doc, inline=False)
        doc = add_source_indent(doc, indent=4)
        defined = defined + "\n" + doc
    defined = defined + "\n" + indent_str + "pass"
    return defined.strip()


def add_source_indent(source: str, indent: int = 4) -> str:
    """
    给代码添加前缀
    """
    source = source.rstrip()
    lines = source.split('\n')
    result = []
    indent_str = ' ' * indent
    for line in lines:
        if line.strip():
            line = indent_str + line
        result.append(line)
    return "\n".join(result)


def strip_source_indent(source_code: str, indent: Optional[int] = None) -> str:
    """
    一个简单的方法, 用来删除代码前面的 indent.
    """
    if indent is None:
        indent = count_source_indent(source_code)
    if indent == 0:
        return source_code
    indent_str = ' ' * indent
    source_lines = source_code.split('\n')
    result_lines = []
    for line in source_lines:
        if line.startswith(indent_str):
            line = line[indent:]
        result_lines.append(line)
    return '\n'.join(result_lines)


def count_source_indent(source_code: str) -> int:
    """
    一个简单的方法, 用来判断一段 python 函数代码的 indent.
    """
    source_lines = source_code.split('\n')
    for line in source_lines:
        right_stripped = line.rstrip()
        if len(right_stripped) == 0:
            continue
        both_stripped = right_stripped.lstrip()
        return len(right_stripped) - len(both_stripped)
    return 0


def parse_doc_string_with_quotes(doc: str, quote='"""') -> str:
    if doc.startswith(quote) and doc.endswith(quote):
        return doc
    doc = doc.strip(quote)
    doc = doc.replace('\\' + quote, quote)
    doc = doc.replace(quote, '\\' + quote)
    return doc.strip()


def add_name_to_set(names: set, name: str) -> set:
    if name in names:
        raise NameError(f'name "{name}" is already defined')
    names.add(name)
    return names


def is_model_class(typ: type) -> bool:
    if not isinstance(typ, type) or inspect.isabstract(typ):
        return False
    return issubclass(typ, BaseModel) or is_typeddict(typ) or issubclass(typ, EntityClass)


def is_model_instance(obj: Any) -> bool:
    return isinstance(obj, ModelObject)


def get_model_object_meta(obj: Any) -> Optional[Dict]:
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj, TypedDict):
        result = {}
        for k, v in obj.items():
            result[k] = v
        return result
    elif isinstance(obj, EntityClass):
        return obj.to_entity_meta()
    return None


def new_model_instance(model: Type[ModelType], meta: Dict) -> ModelType:
    if issubclass(model, EntityClass):
        return model.new_entity(meta)
    else:
        return model(**meta)


def get_default_typehint(val: Any) -> Optional[str]:
    if isinstance(val, BasicTypes):
        if isinstance(val, str):
            return "str"
        elif isinstance(val, bool):
            return 'bool'
        elif isinstance(val, int):
            return 'int'
        elif isinstance(val, float):
            return 'float'
        elif isinstance(val, list):
            return 'list'
        elif isinstance(val, dict):
            return 'dict'
    return None


def is_callable(obj: Any) -> bool:
    return isinstance(obj, Callable)


def is_public_callable(attr: Any) -> bool:
    return isinstance(attr, Callable) and not inspect.isclass(attr) and not attr.__name__.startswith('_')


def get_reflection_prompt(
        r: Reflection,
        prompt: str,
        imports: bool = True,
        extends: bool = True,
        comments: bool = True,
) -> str:
    lines = []
    if imports:
        lines.append(get_import_comment(r.from_module(), r.module_spec(), r.name()))
    if extends:
        lines.append(get_extends_comment(r.extends()))
    if comments:
        lines.append(parse_comments(r.comments()))
    lines.append(prompt)
    return join_prompt_lines(*lines)


def get_calling_modulename(skip: int = 0) -> Optional[str]:
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
        return None
    frame = stack[start][0]

    # module and packagename.
    module_info = inspect.getmodule(frame)
    if module_info:
        mod = module_info.__name__
        return mod
    return None


def get_obj_desc(obj: Any) -> Optional[str]:
    if isinstance(obj, Descriptive):
        return obj.get_description()
    if isinstance(obj, Identifiable):
        return obj.identifier().description
    if hasattr(obj, 'desc'):
        return getattr(obj, 'desc', None)
    if hasattr(obj, "description"):
        return getattr(obj, 'description', None)
    if hasattr(obj, "__desc__"):
        attr = getattr(obj, "__desc__", None)
        if attr:
            return get_str_from_func_or_attr(attr)
    if isinstance(obj, AttrDefaultTypes):
        return str(obj)
    return None


def get_modulename(val: Any) -> Optional[str]:
    module = inspect.getmodule(val)
    if module and hasattr(module, '__name__'):
        return getattr(module, '__name__', None)
    return None
