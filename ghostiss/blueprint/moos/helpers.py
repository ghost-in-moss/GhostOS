# from typing import Any, Optional, Callable, Dict, List, Type, TypedDict, Union, Set
# from abc import ABC, abstractmethod
# import inspect
# import re
# from pydantic import BaseModel
# from ghostiss.blueprint.moos.variable import Var, VarKind
# from ghostiss.container import Provider
#
#
# class DescribeAble(ABC):
#
#     @abstractmethod
#     def description(self) -> str:
#         pass
#
#
# class PromptAble(ABC):
#
#     @abstractmethod
#     def get_prompt(self) -> str:
#         pass
#
#
# class PromptAbleClass(ABC):
#
#     @classmethod
#     @abstractmethod
#     def get_prompt(cls) -> str:
#         pass
#
#
# def get_type(value: Any) -> Optional[type]:
#     if inspect.isclass(value):
#         return None
#     type_ = type(value)
#     if inspect.isclass(type_) and not inspect.isbuiltin(type_):
#         return type_
#     return None
#
#
# def get_module_name(value: Any) -> str:
#     module = inspect.getmodule(value)
#
#
#
# def get_description(value: Any) -> str:
#     """
#     尝试从一个变量身上获取它的描述.
#     """
#     if inspect.isclass(value) or inspect.isfunction(value) or inspect.ismethod(value):
#         return inspect.getdoc(value)
#     if isinstance(value, DescribeAble):
#         return value.description()
#     if hasattr(value, "description"):
#         attr = getattr(value, "description")
#         return get_str_from_func_or_attr(attr)
#     if hasattr(value, "desc"):
#         attr = getattr(value, "description")
#         return get_str_from_func_or_attr(attr)
#     return ""
#
#
# def get_caller_file(backtrace: int = 1) -> str:
#     """
#     返回调用这个方法时所在的文件位置.
#     """
#     stack = inspect.stack()
#     caller_frame = stack[backtrace]
#     return caller_frame.filename
#
#
# def get_caller_module(backtrace: int = 1) -> str:
#     """
#     返回调用这个方法时所在的模块名.
#     """
#     stack = inspect.stack()
#     caller_frame = stack[backtrace]
#     module = inspect.getmodule(caller_frame.frame)
#     if module is None:
#         return ""
#     if module.__name__ == "__main__":
#         return ""
#     return module.__name__
#
#
# def is_typing(value: Any) -> bool:
#     if hasattr(value, "__module__"):
#         return getattr(value, "__module__") == "typing"
#     return False
#
#
# def get_prompt(value: Any) -> str:
#     """
#     从一个变量身上获取 prompt.
#     """
#     if isinstance(value, PromptAble):
#         return value.get_prompt()
#     try:
#         # 如果是类的话.
#         if inspect.isclass(value) and issubclass(value, PromptAbleClass):
#             return value.get_prompt()
#         source = inspect.getsource(value)
#         return source
#     except TypeError:
#         return ""
#
#
# def is_builtin(value: Any) -> bool:
#     if inspect.isbuiltin(value):
#         return True
#     if not inspect.isclass(value):
#         return False
#     return value.__module__ != "__builtin__"
#
#
# def is_classmethod(func: Any) -> bool:
#     """
#     判断一个变量是不是一个 @classmethod.
#     code by moonshot
#     """
#     if not isinstance(func, Callable):
#         return False
#     if not inspect.ismethod(func):
#         return False
#     if not hasattr(func, '__self__'):
#         return False
#     self = getattr(func, '__self__', None)
#     return self is not None and isinstance(self, type)
#
#
# def get_str_from_func_or_attr(value: Any) -> Optional[str]:
#     if isinstance(value, Callable):
#         return value()
#     try:
#         return str(value)
#     except AttributeError:
#         return None
#
#
# def reassign_var_name(var: Var, names: Set[str]) -> Var:
#     pass
#
#
# def count_source_indent(source_code: str) -> int:
#     """
#     一个简单的方法, 用来判断一段 python 函数代码的 indent.
#     """
#     source_lines = source_code.split('\n')
#     for line in source_lines:
#         right_stripped = line.rstrip()
#         if len(right_stripped) == 0:
#             continue
#         both_stripped = right_stripped.lstrip()
#         if len(both_stripped) < len(right_stripped):
#             return len(right_stripped) - len(both_stripped)
#     return 0
#
#
# def strip_source_indent(source_code: str) -> str:
#     """
#     一个简单的方法, 用来删除代码前面的 indent.
#     """
#     indent = count_source_indent(source_code)
#     if indent == 0:
#         return source_code
#     indent_str = ' ' * indent
#     source_lines = source_code.split('\n')
#     result_lines = []
#     for line in source_lines:
#         if line.startswith(indent_str):
#             result_lines.append(line[indent:])
#     return '\n'.join(result_lines)
#
#
# def get_callable_definition(
#         caller: Callable,
#         method_name: Optional[str] = None,
#         doc: Optional[str] = None,
# ) -> str:
#     """
#     将一个 callable 对象的源码剥离方法和描述.
#     """
#     if inspect.isclass(caller) and isinstance(caller, Callable):
#         method_name = method_name or caller.__name__
#         caller = getattr(caller, '__call__')
#         # 使用 __call__ 作为真正的方法.
#         return get_callable_definition(caller, method_name, doc)
#
#     if not inspect.isfunction(caller) and not inspect.ismethod(caller):
#         raise TypeError(f'"{caller}" is not function or method')
#     source_code = inspect.getsource(caller)
#     stripped_source = strip_source_indent(source_code)
#     source_lines = stripped_source.split('\n')
#     definition = []
#
#     for line in source_lines:
#         # if line.startswith('def ') or len(definition) > 0:
#         line = line.strip()
#         if line == "@abstractmethod":
#             continue
#         definition.append(line)
#         code_line = line.split('#')[0]
#         if code_line.rstrip().endswith(':'):
#             break
#     defined = '\n'.join(definition).strip()
#     if method_name:
#         found = re.search(r'def\s+(\w+)\(', defined)
#         if found:
#             defined = defined.replace(found.group(0), "def {name}(".format(name=method_name), 1)
#     indent = ' ' * 4
#     if doc is None:
#         doc = inspect.getdoc(caller)
#     if doc:
#         doc_lines = doc.split('\n')
#         doc_block = [indent + '"""']
#         for line in doc_lines:
#             line = line.replace('"""', '\\"""')
#             doc_block.append(indent + line)
#         doc_block.append(indent + '"""')
#         doc = '\n'.join(doc_block)
#         defined = defined + "\n" + doc
#     defined = defined + "\n" + indent + "pass"
#     return defined.strip()
#
#
# def add_source_indent(source: str, indent: int = 4) -> str:
#     """
#     给代码添加前缀
#     """
#     lines = source.split('\n')
#     result = []
#     indent_str = ' ' * indent
#     for line in lines:
#         if line.strip():
#             line = indent_str + line
#         result.append(line)
#     return "\n".join(result)
#
#
# def is_caller(value: Any) -> bool:
#     return isinstance(value, Callable)
#
#
# def is_model_class(value: Any) -> bool:
#     # todo: 未来添加更多的 model.
#     return isinstance(value, type) and (issubclass(value, BaseModel) or issubclass(value, TypedDict))
#
#
# def get_attr_prompt(name: str, type_hint: Optional[str], doc: Optional[str]) -> str:
#     type_hint_mark = ""
#     if type_hint:
#         type_hint_mark = f": {type_hint}"
#     doc_mark = ""
#     if doc:
#         doc_mark = f'\n"""{doc}"""'
#     return name + type_hint_mark + doc_mark
