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

BasicTypes = Union[str, int, float, bool, list, dict]
"""scalar types"""

AttrDefaultTypes = Union[int, float, bool]

ModelObject = Union[BaseModel, TypedDict, EntityClass]

ModelType = Union[Type[BaseModel], Type[TypedDict], Type[EntityClass]]


class Reflection(ABC):
    """
    对任意值的封装, 提供面向 LLM 的 Prompt, 并且支持 import Reflection 并且添加到 MOSS
    """

    def __init__(
            self,
            name: str,
            doc: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            typehint: Optional[Union[str, Any]] = None,
            comments: Optional[str] = None,
            prompt: Optional[str] = None,
            extends: Optional[List[Any]] = None,
    ):
        self._name = name
        self._doc = doc
        self._module = module
        self._module_spec = module_spec
        self._comments = comments
        self._typehint = typehint
        self._prompt = prompt
        self._extends = extends

    def name(self) -> str:
        """
        reflection name:
        1. variable name
        2. attribute name
        3. method name
        4. class name
        """
        return self._name

    @abstractmethod
    def value(self) -> Any:
        """
        real value of the reflection
        """
        pass

    def prompt(self) -> str:
        """
        get the prompt of the reflection
        """
        if not self._prompt:
            self._prompt = self.generate_prompt()
        return self._prompt

    @abstractmethod
    def generate_prompt(self) -> str:
        pass

    def module(self) -> Optional[str]:
        return self._module

    def module_spec(self) -> Optional[str]:
        return self._module_spec

    def extends(self) -> Optional[List[Any]]:
        return self._extends

    def comments(self) -> Optional[str]:
        return self._comments

    def typehint(self) -> Optional[Union[str, Any]]:
        return self._typehint

    def update(
            self,
            *,
            name: Optional[str] = None,
            doc: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            typehint: Optional[Union[str, Any]] = None,
            comments: Optional[str] = None,
            prompt: Optional[str] = None,
            extends: Optional[List[Any]] = None,
    ) -> "Reflection":
        if name is not None:
            self._name = name
        if doc is not None:
            self._doc = doc
        if module:
            self._module = module
        if module_spec:
            self._module_spec = module_spec
        if typehint is not None:
            self._typehint = typehint
        if comments is not None:
            self._comments = comments
        if prompt is not None:
            self._prompt = prompt
        if extends is not None:
            self._extends = extends
        return self


class IterableReflection(Reflection, ABC):

    @abstractmethod
    def iterate(self) -> Iterable[Reflection]:
        pass

    def generate_prompt(self) -> str:
        return ""


class ValueReflection(Reflection, ABC):
    """
    值的反射, 是一个具体的 object 或某个类型的实例.
    """
    pass


class TypeReflection(Reflection, ABC):
    """
    类型的反射.
    """
    pass


class CallerReflection(Reflection, ABC):
    """
    callable 对象的反射.
    """
    pass


class Importing(Reflection):
    """
    特殊的反射类型, 在上下文中没有独立的 prompt, 只有 from xxx import xxx.
    当类库知识对于 LLM 是先验的情况下, 应该生成这种.
    """

    @classmethod
    def iterate(cls, values: Iterable[Union[Any, Tuple[str, Any]]], module: Optional[str] = None) -> List["Importing"]:
        result = []
        for value in values:
            if isinstance(value, Tuple):
                name, value = value
                result.append(cls(value=value, module=module, name=name))
            else:
                result.append(cls(value=value, module=module))
        return result

    def __init__(
            self,
            *,
            value: Any,
            name: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
    ):
        self._cls = value
        is_module = inspect.ismodule(value)
        if not module:
            if is_module:
                module = value.__name__
            elif hasattr(value, '__module__'):
                module = getattr(value, '__module__')
            else:
                module = None
        if not module_spec and not is_module:
            module_spec = getattr(value, '__name__', None)
        if not name:
            name = module if is_module else module_spec
        super().__init__(
            name=name,
            module=module,
            module_spec=module_spec,
        )

    def value(self) -> Any:
        return self._cls

    def generate_prompt(self) -> str:
        if self._module_spec:
            prompt = f"from {self._module} import {self._module_spec}"
        else:
            prompt = f"import {self._module}"
        if self._name:
            prompt += " as " + self._name
        return prompt


class Attr(ValueReflection):
    """
    实现类的属性, 可以挂载到一个虚拟类上, 并提供 Prompt.
    """

    def __init__(
            self, *,
            name: str,
            value: Any,
            typehint: Optional[Any] = None,
            extends: Optional[List[Any]] = None,
            prompt: Optional[str] = None,
            doc: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            print_val: Optional[bool] = None,
            comments: Optional[str] = None,
    ):
        """
        初始化一个 Attr.

        :param name: Attr 的 name.
        :param value: 任意类型, 但主要分为: 1. 标量; 2. 实例; 3. typehint
        :param prompt: 如果 prompt 不为 None, 默认使用它作为 prompt.
        :param typehint: 描述 value 的类型. 如果是 str 就直接展示, 否则暂时为 'str(typehint)'. BasicTypes 类型的 values 默认展示.
        :param extends: 强调 value 实现了什么类型. 会添加为注释: # extends xxx, yyy.  推荐使用 str 来描述.
        :param doc: 给属性添加 doc. 符合 python 标准.
        :param module: 指定所属的 module
        :param module_spec: 指定从 module 的 spec 中 import. 不一定是真实的.
        :param print_val: 决定 attr 的 prompt 是否展示其赋值.
        :param comments: 提供额外的注释, 必须以 # 开头.
        """
        self._value = value
        if typehint is None and isinstance(value, BasicTypes):
            typehint = get_default_typehint(value)
        # 如果是 typing 里的类型, 则默认打印其赋值. 比如 foo = Union[str, int]
        self._print_val = True if is_typing(value) or isinstance(value, AttrDefaultTypes) else print_val
        super().__init__(
            name=name,
            doc=doc,
            module=module,
            module_spec=module_spec,
            extends=extends,
            comments=comments,
            typehint=typehint,
            prompt=prompt,
        )

    def value(self) -> Any:
        return self._value

    def generate_prompt(self) -> str:
        comments = parse_comments(self._comments)
        name = self.name()
        import_from = get_import_comment(self._module, self._module_spec, self.name())
        extends = get_extends_comment(self._extends)
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
            extends,
            comments,
            name + typehint + value,
            doc,
        )


class DictAttr(Attr):
    """
    实现一个 dict 型的属性.
    会尝试将 key 和 value 的描述用 doc 写出来. 类似:

    foo: value of foo
    bar: 123
    """

    def __init__(
            self, *,
            name: str,
            values: Dict[str, Any],
            item_type: Optional[Type] = None,
            typehint: Optional[Any] = None,
            doc: Optional[str] = None,
            descriptions: Optional[Dict[str, str]] = None,
            prompt: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            extends: Optional[List[Any]] = None,
            comments: Optional[str] = None,
    ):
        if typehint is None and item_type:
            typehint = Dict[str, item_type]
        if descriptions is None:
            descriptions = {}
            for key, val in values.items():
                if isinstance(val, Descriptive):
                    descriptions[key] = val.get_description()
                elif isinstance(val, Identifiable):
                    descriptions[key] = val.identifier().description
                else:
                    desc = get_obj_desc(val)
                    if desc is not None:
                        descriptions[key] = desc

        if descriptions:
            lines = [doc, "The descriptions of the items:"]
            for name, desc in descriptions.items():
                lines.append(f"`{name}`: {desc}")
            doc = join_prompt_lines(*lines)

        super().__init__(
            name=name,
            value=values,
            typehint=typehint,
            prompt=prompt,
            module=module,
            module_spec=module_spec,
            extends=extends,
            comments=comments,
            doc=doc,
        )


class Typing(TypeReflection):

    def __init__(
            self, *,
            typing: Any,
            name: Optional[str] = None,
    ):
        if not is_typing(typing):
            raise TypeError(f"'{typing}' is not a typing variable")
        self._typing = typing
        super().__init__(name=name)

    def generate_prompt(self) -> str:
        return f"{self._name} = {self._typing}"

    def value(self) -> Any:
        return self._typing


class Method(CallerReflection):
    """
    将一个 Callable 对象封装成 Method, 可以添加到 MOSS 上.
    """

    def __init__(
            self, *,
            caller: Callable,
            name: Optional[str] = None,
            doc: Optional[str] = None,
            prompt: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            comments: Optional[str] = None,
            typehint: Optional[Callable] = None,
    ):
        """
        :param caller: callable object, may be function, method or object that callable
        :param name: alias name for the method
        :param doc: replace the origin doc string
        :param prompt:
        :param module:
        :param module_spec:
        :param comments:
        """
        self._caller = caller
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
            prompt=prompt,
            typehint=typehint,
        )

    def value(self) -> Callable:
        return self._caller

    def generate_prompt(self) -> str:
        caller = self._typehint if self._typehint else self._caller
        prompt = parse_callable_to_method_def(caller=caller, alias=self.name(), doc=self._doc)
        return prompt


class SourceCode(TypeReflection):

    def __init__(
            self, *,
            cls: Type,
            typehint: Optional[Type] = None,
            name: Optional[str] = None,
            prompt: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            comments: Optional[str] = None,
            extends: Optional[List[Any]] = None,
    ):
        if not inspect.isclass(cls):
            raise TypeError(f"type '{cls}' is not a class type")
        if typehint and not inspect.isclass(typehint):
            raise TypeError(f"'typehint {typehint}' is not a class type")
        name = name
        if not name:
            name = module_spec
        if not name:
            name = cls.__name__
        self._cls = cls
        self._typehint_type = typehint
        if module is None:
            module = cls.__module__
        if module_spec is None:
            module_spec = cls.__name__

        super().__init__(
            name=name,
            prompt=prompt,
            module=module,
            module_spec=module_spec,
            comments=comments,
            extends=extends,
            typehint=typehint,
        )

    def value(self) -> Any:
        return self._cls

    def generate_prompt(self) -> str:
        if self._typehint_type:
            type_ = self._typehint_type
        else:
            type_ = self._cls

        source = inspect.getsource(type_)
        source = strip_source_indent(source)
        source = replace_class_def_name(source, self.name())
        return source


class Class(TypeReflection):
    """
    对一个类型的封装.
    类型通常需要放到 Locals 里对外展示.
    """

    def __init__(
            self, *,
            cls: type,
            prompt: Optional[str] = None,
            name: Optional[str] = None,
            comments: Optional[str] = None,
            doc: Optional[str] = None,
            typehint: Optional[type] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            extends: Optional[List[Any]] = None,
    ):
        if not inspect.isclass(cls):
            raise TypeError(f"Class must be a class, not {cls}")

        self._cls = cls
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
            prompt=prompt,
            typehint=typehint,
            extends=extends,
        )

    def value(self) -> type:
        return self._cls

    def generate_prompt(self) -> str:
        prompt = self._prompt
        if not prompt:
            cls = self._typehint if self._typehint else self._cls
            source = inspect.getsource(cls)
            prompt = make_class_prompt(source=source, name=self._name, doc=self._doc, attrs=None)
        return prompt


class ClassPrompter(Class):
    """
    自由拼装一个类的 Prompt. 可以指定:
    1. constructor: __init__ 方法.
    2. methods
    3. attrs
    """

    def __init__(
            self, *,
            cls: type,
            name: Optional[str] = None,
            prompt: Optional[str] = None,
            doc: Optional[str] = None,
            constructor: Optional[Method] = None,
            attrs: Optional[Iterable[Attr]] = None,
            methods: Optional[Iterable[Method]] = None,
            typehint: Optional[Any] = None,
            comments: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            extends: Optional[List[Any]] = None,
    ):
        if not inspect.isclass(cls):
            raise TypeError(f"Class must be a class, not {cls}")
        self._attrs = attrs
        self._constructor: Optional[Method] = constructor
        self._methods = methods
        if module is None:
            module = inspect.getmodule(cls).__name__
        if module_spec is None:
            module_spec = cls.__name__

        super().__init__(
            cls=cls,
            prompt=prompt,
            doc=doc,
            name=name,
            typehint=typehint,
            comments=comments,
            module=module,
            module_spec=module_spec,
            extends=extends,
        )

    def generate_prompt(self) -> str:
        cls = self._typehint if self._typehint else self._cls
        source = inspect.getsource(cls)
        doc = self._doc
        if not doc:
            doc = cls.__doc__
        __names: set = set()
        __name = self.name()
        __attr_prompts: List[str] = []
        constructor = self._constructor
        if constructor:
            __names = add_name_to_set(__names, '__init__')
            constructor = constructor.update(name='__init__')
            __attr_prompts.append(constructor.prompt())
        attrs = self._attrs
        if attrs:
            for attr in attrs:
                __names = add_name_to_set(__names, attr.name())
                __attr_prompts.append(attr.prompt())
        methods = self._methods
        if methods:
            for method in methods:
                __names = add_name_to_set(__names, method.name())
                __attr_prompts.append(method.prompt())
        prompt = make_class_prompt(source=source, name=__name, doc=doc, attrs=__attr_prompts)
        return prompt


class BuildObject(Attr):
    """
    使用 Attr & Method 组装出一个临时对象.
    """

    def __init__(
            self, *,
            name: str,
            attrs: Optional[Iterable[Attr]] = None,
            methods: Optional[Iterable[Method]] = None,
            typehint: Optional[Any] = None,
            extends: Optional[List[Any]] = None,
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
            extends=extends,
            doc=doc,
            module=module,
            module_spec=module_spec,
            comments=comments,
        )


class Interface(ClassPrompter):
    """
    只暴露指定 public 方法的类.
    """

    def __init__(
            self, *,
            cls: type,
            name: Optional[str] = None,
            include_methods: Optional[Iterable[str]] = None,
            doc: Optional[str] = None,
            comments: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            extends: Optional[List[Any]] = None,
    ):
        allows = None
        if include_methods is not None:
            allows = set(include_methods)
        target = cls
        if module is None:
            module = get_modulename(cls)
        if module_spec is None:
            module_spec = cls.__name__
        if name is None:
            name = cls.__name__

        members = inspect.getmembers(target, predicate=is_public_callable)
        members = [] if members is None else members
        methods_reflections = []
        for mem_name, member in members:
            allowed = (allows is None and not mem_name.startswith("_")) or (allows is not None and mem_name in allows)
            if not allowed:
                continue
            _method_reflect = Method(
                caller=member,
                name=mem_name,
            )
            methods_reflections.append(_method_reflect)
        super().__init__(
            cls=cls,
            name=name,
            methods=methods_reflections,
            doc=doc,
            comments=comments,
            module=module,
            module_spec=module_spec,
            extends=extends,
        )


class ClassSign(Interface):
    """
    只暴露 class + doc 的类.
    """

    def __init__(
            self, *,
            cls: type,
            name: Optional[str] = None,
            doc: Optional[str] = None,
            comments: Optional[str] = None,
            module: Optional[str] = None,
            module_spec: Optional[str] = None,
            extends: Optional[List[Any]] = None,
    ):
        if module is None:
            module = inspect.getmodule(cls).__name__
        if module_spec is None:
            module_spec = cls.__name__

        super().__init__(
            cls=cls,
            name=name,
            include_methods=[],
            doc=doc,
            comments=comments,
            module=module,
            module_spec=module_spec,
            extends=extends,
        )


class Locals(ValueReflection):
    """
    local variables
    """

    def __init__(
            self,
            methods: Optional[Iterable[CallerReflection]] = None,
            types: Optional[Iterable[TypeReflection]] = None,
            imported: Optional[Iterable[Importing]] = None,
            prompt: Optional[str] = None,
    ):
        self.__imported = imported
        self.__locals: Dict[str, Reflection] = {}
        self.__local_var_orders: List[str] = []
        if methods:
            for method in methods:
                name = method.name()
                if name in self.__locals:
                    raise NameError(f"Duplicate method name: {name}")
                self.__local_var_orders.append(name)
                self.__locals[method.name()] = method
        if types:
            for type_reflection in types:
                name = type_reflection.name()
                if name in self.__locals:
                    raise NameError(f"Duplicate method name: {name}")
                self.__local_var_orders.append(name)
                self.__locals[name] = type_reflection
        super().__init__(
            name="",
            prompt=prompt,
        )

    def value(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for name, reflection in self.__locals.items():
            result[name] = reflection.value()
        return result

    def generate_prompt(self) -> str:
        prompts = []
        imported: Dict[str, List[str]] = {}
        modules = []
        for imp in self.__imported:
            module = imp.module()
            spec = imp.module_spec()
            if not module and not spec:
                continue
            if module not in imported:
                imported[module] = []
                modules.append(module)
            if spec:
                specs = imported[module]
                specs.append(spec)
                imported[module] = specs

        imported_lines = []
        for module in modules:
            specs = imported[module]
            if not specs:
                line = "import {module}".format(module=module)
            else:
                line = "from {module} import ({specs})".format(module=module, specs=",".join(specs))
            imported_lines.append(line)
        if len(imported_lines) > 0:
            prompts.append("\n".join(imported_lines))

        for name in self.__local_var_orders:
            reflection = self.__locals[name]
            prompt = reflection.prompt()
            type_prompt = get_reflection_prompt(reflection, prompt=prompt)
            prompts.append(type_prompt)
        return "\n\n".join(prompts)


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
        lines.append(get_import_comment(r.module(), r.module_spec(), r.name()))
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
