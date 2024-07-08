import inspect
import re
from typing import Any, Dict, Callable, Optional, List, Iterable, TypedDict, Union
from abc import ABC, abstractmethod
from pydantic import BaseModel
from ghostiss.entity import EntityClass

__all__ = [
    'BasicTypes',
    'Reflection',
    'Attr',
    'Class',
    'ClassPrompter', 'Library', 'Interface',
    'Locals',
    'reflect', 'reflects',
    'is_callable', 'is_typing', 'is_public_callable', 'is_builtin', 'is_classmethod', 'is_model_class',
    'parse_comments', 'parse_doc_string', 'parse_doc_string_with_quotes', 'parse_callable_to_method_def',
    'get_typehint_string', 'get_default_typehint', 'get_import_comment', 'get_implement_comment',
    'get_str_from_func_or_attr',
    'get_class_def_from_source',
]

BasicTypes = Union[str, int, float, bool, list, dict]


class Reflection(ABC):

    def __init__(
            self,
            name: str,
            doc: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            comments: Optional[str] = None,
    ):
        self._name = name
        self._doc = doc
        self._module = module
        self._module_spec = module_spec
        self._comments = comments

    def name(self) -> str:
        return self._name

    @abstractmethod
    def value(self) -> Any:
        pass

    @abstractmethod
    def prompt(self) -> str:
        pass

    def module(self) -> Optional[str]:
        return self._module

    def module_spec(self) -> Optional[str]:
        return self._module_spec

    def with_name(self, name: str) -> "Reflection":
        self._name = name
        return self

    def with_from(self, module: str, module_spec: str) -> "Reflection":
        self._module = module
        self._module_spec = module_spec
        return self


class Attr(Reflection):

    def __init__(
            self, *,
            name: str,
            value: Any,
            typehint: Optional[Any] = None,
            implements: Optional[List[Any]] = None,
            prompt: Optional[str] = None,
            doc: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            print_val: Optional[bool] = None,
            comments: Optional[str] = None,
    ):
        self._value = value
        if typehint is None and isinstance(value, BasicTypes):
            typehint = get_default_typehint(value)
        self._typehint = typehint
        self._implements = implements
        self._doc = doc
        self._prompt = prompt
        self._print_val = print_val
        super().__init__(
            name=name,
            doc=doc,
            module=module,
            module_spec=module_spec,
            comments=comments,
        )

    def value(self) -> Any:
        return self._value

    def prompt(self) -> str:
        if self._prompt is not None:
            return self._prompt

        comments = parse_comments(self._comments)
        name = self.name()
        import_from = get_import_comment(self._module, self._module_spec, self.name())
        implements = get_implement_comment(self._implements)
        typehint = get_typehint_string(self._typehint)
        value = ""
        if self._print_val is not None and self._print_val:
            if isinstance(self._value, str):
                value = f" = '{self._value}'"
            else:
                value = f" = {self._value}"
        doc = parse_doc_string(self._doc, inline=True)
        return join_prompt_lines(
            import_from,
            implements,
            comments,
            name + typehint + value,
            doc,
        )


class Method(Reflection):

    def __init__(
            self, *,
            caller: Callable,
            alias: Optional[str] = None,
            doc: Optional[str] = None,
            prompt: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            comments: Optional[str] = None,
    ):
        self._caller = caller
        self._prompt = prompt
        name = alias
        if not name:
            name = module_spec
        if not name:
            name = caller.__name__
        super().__init__(
            name=name,
            doc=doc,
            module=module,
            module_spec=module_spec,
            comments=comments,
        )

    def value(self) -> Callable:
        return self._caller

    def prompt(self) -> str:
        if self._prompt is not None:
            return self._prompt

        prompt = parse_callable_to_method_def(caller=self._caller, alias=self.name(), doc=self._doc)
        comments = parse_comments(self._comments)
        import_from = get_import_comment(self._module, self._module_spec, self.name())
        return join_prompt_lines(comments, import_from, prompt)


class Class(Reflection):

    def __init__(
            self, *,
            cls: type,
            prompt: Optional[str] = None,
            alias: Optional[str] = None,
            comments: Optional[str] = None,
            doc: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            implements: Optional[List[Any]] = None,
    ):
        if not inspect.isclass(cls):
            raise TypeError(f"Class must be a class, not {cls}")

        self._cls = cls
        self._prompt = prompt
        self._implements = implements
        name = alias
        if not name:
            name = module_spec
        if not name:
            name = cls.__name__
        super().__init__(
            name=name,
            doc=doc,
            module=module,
            module_spec=module_spec,
            comments=comments,
        )

    def value(self) -> type:
        return self._cls

    def prompt(self) -> str:
        comments = parse_comments(self._comments)
        implementation = get_implement_comment(self._implements)
        import_from = get_import_comment(self._module, self._module_spec, self.name())
        prompt = self._prompt
        if not prompt:
            source = inspect.getsource(self._cls)
            prompt = make_class_prompt(source=source, name=self._name, doc=self._doc, attrs=None)
        return join_prompt_lines(comments, import_from, implementation, prompt)


class ClassPrompter(Class):

    def __init__(
            self, *,
            cls: type,
            alias: Optional[str] = None,
            doc: Optional[str] = None,
            constructor: Optional[Method] = None,
            attrs: Optional[Iterable[Attr]] = None,
            methods: Optional[Iterable[Method]] = None,
            comments: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            implements: Optional[List[Any]] = None,
    ):
        if not inspect.isclass(cls):
            raise TypeError(f"Class must be a class, not {cls}")

        source = inspect.getsource(cls)
        if not doc:
            doc = cls.__doc__
        __names: set = set()
        __name = alias if alias else cls.__name__
        __attr_prompts: List[str] = []
        if constructor:
            __names = add_name_to_set(__names, constructor.name())
            __attr_prompts.append(constructor.prompt())
        if attrs:
            for attr in attrs:
                __names = add_name_to_set(__names, attr.name())
                __attr_prompts.append(attr.prompt())
        if methods:
            for method in methods:
                __names = add_name_to_set(__names, method.name())
                __attr_prompts.append(method.prompt())
        prompt = make_class_prompt(source=source, name=__name, doc=doc, attrs=__attr_prompts)

        super().__init__(
            cls=cls,
            prompt=prompt,
            alias=alias,
            comments=comments,
            module=module,
            module_spec=module_spec,
            implements=implements,
        )


class BuildObject(Attr):

    def __init__(
            self, *,
            name: str,
            attrs: Optional[Iterable[Attr]] = None,
            methods: Optional[Iterable[Method]] = None,
            typehint: Optional[Any] = None,
            implements: Optional[List[Any]] = None,
            doc: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            comments: Optional[str] = None,
    ):
        class Temp:
            pass

        value = Temp()
        if attrs:
            for attr in attrs:
                setattr(value, attr.name(), attr.value())
        if methods:
            for method in methods:
                setattr(value, method.name(), method.value())
        super().__init__(
            name=name,
            value=value,
            typehint=typehint,
            implements=implements,
            doc=doc,
            module=module,
            module_spec=module_spec,
            comments=comments,
        )


class Library(ClassPrompter):
    def __init__(
            self, *,
            cls: type,
            alias: Optional[str] = None,
            methods: Optional[Iterable[str]] = None,
            doc: Optional[str] = None,
            comments: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            implements: Optional[List[Any]] = None,
    ):
        allows = None
        if methods is not None:
            allows = set(methods)
        target = cls
        members = inspect.getmembers(target, predicate=is_public_callable)
        members = [] if members is None else members
        methods_reflections = []
        for name, member in members:
            allowed = (allows is None and not name.startswith("_")) or (allows is not None and name in allows)
            if not allowed:
                continue
            _method_reflect = Method(
                caller=member,
                alias=name,
            )
            methods_reflections.append(_method_reflect)
        super().__init__(
            cls=cls,
            alias=alias,
            methods=methods_reflections,
            doc=doc,
            comments=comments,
            module=module,
            module_spec=module_spec,
            implements=implements,
        )


class Interface(Library):

    def __init__(
            self, *,
            cls: type,
            alias: Optional[str] = None,
            doc: Optional[str] = None,
            comments: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            implements: Optional[List[Any]] = None,
    ):
        super().__init__(
            cls=cls,
            alias=alias,
            methods=[],
            doc=doc,
            comments=comments,
            module=module,
            module_spec=module_spec,
            implements=implements,
        )


class Locals(Reflection):

    def __init__(
            self,
            methods: Optional[Iterable[Method]] = None,
            classes: Optional[Iterable[Class]] = None,
    ):
        self.methods = methods
        self.classes = classes
        super(Reflection).__init__(
            name="",
        )

    def value(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.methods:
            for method in self.methods:
                result[method.name()] = method.value()
        if self.classes:
            for cls in self.classes:
                result[cls.name()] = cls.value()
        return result

    def prompt(self) -> str:
        prompts = []
        if self.methods:
            for method in self.methods:
                prompts.append(method.prompt())
        if self.classes:
            for cls in self.classes:
                prompts.append(cls.prompt())
        return "\n\n".join(prompts)


def reflect(
        *,
        var: Any,
        name: Optional[str] = None,
        module: Optional[str] = None,
        module_spec: Optional[str] = None,
        doc: Optional[str] = None,
        comments: Optional[str] = None,
) -> Optional[Reflection]:
    if isinstance(var, Reflection):
        if module and module_spec:
            var = var.with_from(module_spec=module_spec, module=module)
        if name:
            var = var.with_name(name)
        return var

    elif is_builtin(var):
        return None

    elif is_typing(var):
        if not name:
            raise ValueError('Name must be a non-empty string for typing')
        return Attr(name=name, value=var, doc=doc, comments=comments, module=module, module_spec=module_spec)
    elif isinstance(var, type):
        if is_model_class(var):
            # todo
            pass
        else:
            return Class(cls=var, alias=name, doc=doc, comments=comments, module=module, module_spec=module_spec)
    elif isinstance(var, Callable):
        return Method(caller=var, alias=name, doc=doc, comments=comments, module=module, module_spec=module_spec)
    else:
        return None


def reflects(*args, **kwargs) -> Iterable[Reflection]:
    for arg in args:
        r = reflect(var=arg)
        if r is not None:
            yield r
    for k, v in kwargs.items():
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


def get_implement_comment(implements: Optional[List[Any]]) -> Optional[str]:
    if not implements:
        return None
    result = []
    for imp in implements:
        if not imp:
            continue
        elif isinstance(imp, str):
            result.append(imp)
        else:
            result.append('"' + str(imp) + '"')
    return "# implements " + ", ".join(result)


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
        return ": " + typehint
    if is_typing(typehint):
        return ": " + str(typehint)
    else:
        return ': "' + str(typehint) + '"'


def parse_doc_string(doc: Optional[str], inline: bool = True, quote: str = '"""') -> str:
    if not doc:
        return ""
    gap = "" if inline else "\n"
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
    class_def = get_class_def_from_source(source)
    class_def = replace_class_def_name(class_def, name)
    blocks = []
    if doc:
        doc = parse_doc_string(doc, inline=False, quote='"""')
        blocks.append(doc)
    if attrs:
        for attr in attrs:
            blocks.append(attr)
    if len(blocks) == 0:
        blocks.append("pass")

    i = 0
    for block in blocks:
        _block = add_source_indent(block, 4)
        exp = "\n\n" if i > 0 else "\n"
        class_def += exp + _block
        i += 1
    return class_def


def replace_class_def_name(class_def: str, new_name: str) -> str:
    found = re.search(r'class\s+\w+[\(:]', class_def)
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
    return value.__module__ != "__builtin__"


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
        if isinstance(caller, Callable) and hasattr(caller, '__call__'):
            real_caller = getattr(caller, '__call__')
            if not alias:
                alias = type(caller).__name__
            if not doc:
                doc = caller.__doc__ or ""
            return parse_callable_to_method_def(real_caller, alias, doc)
        raise TypeError(f'"{caller}" is not function or method')

    source_code = inspect.getsource(caller)
    stripped_source = strip_source_indent(source_code)
    source_lines = stripped_source.split('\n')
    definition = []

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
    indent = ' ' * 4
    if doc is None:
        doc = inspect.getdoc(caller)
    if doc:
        doc_lines = doc.split('\n')
        doc_block = [indent + '"""']
        for line in doc_lines:
            line = line.replace('"""', '\\"""')
            doc_block.append(indent + line)
        doc_block.append(indent + '"""')
        doc = '\n'.join(doc_block)
        defined = defined + "\n" + doc
    defined = defined + "\n" + indent + "pass"
    return defined.strip()


def add_source_indent(source: str, indent: int = 4) -> str:
    """
    给代码添加前缀
    """
    lines = source.split('\n')
    result = []
    indent_str = ' ' * indent
    for line in lines:
        if line.strip():
            line = indent_str + line
        result.append(line)
    return "\n".join(result)


def strip_source_indent(source_code: str) -> str:
    """
    一个简单的方法, 用来删除代码前面的 indent.
    """
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
    doc.replace('\\' + quote, quote)
    doc.replace(quote, '\\' + quote)
    return doc.strip()


def add_name_to_set(names: set, name: str) -> set:
    if name in names:
        raise NameError(f'name "{name}" is already defined')
    names.add(name)
    return names


def is_model_class(typ: type) -> bool:
    return issubclass(typ, BaseModel) or issubclass(typ, TypedDict) or issubclass(typ, EntityClass)


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
