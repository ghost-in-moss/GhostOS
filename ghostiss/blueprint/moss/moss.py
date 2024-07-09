from typing import List, Set, Dict, Any, Optional, Union, TypedDict, Iterable, Type, Callable
from abc import ABC, abstractmethod
import re
import inspect
from contextlib import redirect_stdout
from pydantic import BaseModel
from importlib.abc import MetaPathFinder
from ghostiss.container import Container, CONTRACT
from ghostiss.blueprint.moss.variable import Var, VarKind, Descriptive, ClassVar, ModelType, lib
from ghostiss.blueprint.moss.context import PyContext, Define, Import
from ghostiss.blueprint.moss.importer import Importer
from ghostiss.helpers import camel_to_snake
from ghostiss.container import Provider
from ghostiss.helpers import BufferPrint

AttrTypes = Union[int, float, str, bool, list, dict, None, Provider, ModelType]


class MOSS(ABC):
    """
    language Model-oriented Operating System Simulation
    full python code interface for large language models
    """

    # --- 创建 MoOS 的方法 --- #

    @abstractmethod
    def new(self, *named_vars, **variables) -> "MOSS":
        """
        return a new instance
        """
        pass

    @abstractmethod
    def add_method(
            self,
            method: Callable,
            *,
            alias: Optional[str] = None,
            doc: Optional[str] = None,
            prompt: Optional[str] = None,
    ) -> None:
        """
        attach a method to MoOS
        :param method: any callable such as function, method, callable object
        :param alias: use custom alias replace of the method.__name__
        :param doc: use custom docstring replace of the method.__doc__
        :param prompt: use custom prompt, not default code prompt generator
        """
        pass

    @abstractmethod
    def set_attr(
            self,
            value: AttrTypes,
            *,
            name: Optional[str] = None,
            implements: Optional[type] = None,
            prompt: Optional[str] = None,
            doc: Optional[str] = None,
    ) -> None:
        """
        attach a value as attribute to MoOS instance.

        :param value: value cant be any object, when it is a Provider, will use it factory to make an instance attribute.
        :param name: attr name
        :param implements: if defined, will announce the attribute typehint is the implements.
        :param prompt: 
        :param doc: 
        """
        pass

    @abstractmethod
    def add_type(
            self,
            typ: Type[CONTRACT],
            *,
            alias: Optional[str] = None,
            prompt: Optional[str] = None,
            doc: Optional[str] = None,
            implements: Optional[List[type]] = None,
    ) -> str:
        pass

    @abstractmethod
    def update_context(self, context: PyContext) -> None:
        """
        为 MoOS 添加更多的变量, 可以覆盖掉之前的.
        :param context:
        :return:
        """
        pass

    # --- MoOS 默认暴露的基础方法 --- #

    @abstractmethod
    def imports(self, module: str, *specs: str, **aliases: str) -> Dict[str, Any]:
        """
        import from module
        :param module: module name
        :param specs: module spec
        :param aliases: alias=module spec
        :return: values mapped by name to value

        example:
        'from module.a import Foo, Bar as bar'
        could be .imports('module.a', 'Foo', bar='Bar')
        """
        pass

    @abstractmethod
    def print(self, *args, **kwargs) -> None:
        """
        replace builtin print
        """
        pass

    @abstractmethod
    def flush(self) -> str:
        """
        flush printed output
        :return: str
        """
        pass

    @abstractmethod
    def define(
            self,
            name: str,
            value: Union[str, int, float, bool, Dict, List, BaseModel],
            desc: Optional[str] = None,
    ) -> Any:
        """
        定义一个变量, 这个变量会保留到下一轮会话中.
        :param name:
        :param value:
        :param desc:
        :return:
        """
        pass

    # --- 对上层系统暴露的方法 --- #

    @abstractmethod
    def bootstrap(self) -> Dict[str, Any]:
        """
        返回 moos 运行时的上下文变量, 可以结合 exec 提供 locals 并且运行.
        """
        pass

    @abstractmethod
    def dump_context(self) -> PyContext:
        """
        返回当前的可存储上下文.
        """
        pass

    @abstractmethod
    def dump_code_prompt(self) -> str:
        """
        获取可以描述相关上下文变量的 prompt.
        预期形态为:

        class Contract:
           ...

        class LibType:
           ...

        def caller1():
           ...

        class MoOS(ABC):
           '''
           注解
           '''

           var1: typehint
           ''' var 1 desc '''

           var2: typehint
           ''' var 2 desc'''

           lib1: LibType
        """
        pass

    def destroy(self) -> None:
        """
        方便垃圾回收.
        """
        pass

    # --- 运行逻辑 --- #

    def __call__(
            self,
            code: str,
            result_name: str = "",
            update_locals: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        基于 moos 提供的上下文, 运行一段代码.
        :param code: 需要运行的代码.
        :param result_name: 指定一个变量名用来获取返回值. 如果为空, 则返回 None.
        :param update_locals: 额外添加到上下文里的 locals 变量. 但这些变量不会生成 code prompt.
        :return: 根据 result_name 从 code 中获取返回值.
        :exception: any exception will be raised, handle them outside
        """
        local_values = self.bootstrap()
        if update_locals is not None:
            local_values.update(update_locals)
        if result_name and result_name not in local_values:
            # 对 result_name 做初始化.
            local_values[result_name] = None
        local_values['print'] = self.print
        # 执行代码. 注意!! 暂时没有考虑任何安全性问题. 理论上应该全部封死.
        # 考虑使用 RestrictPython
        exec(code, globals(), local_values)
        if result_name:
            return local_values[result_name]
        return None


class BaseMOSS(MOSS):

    def __init__(self, *, doc: str, container: Container):
        self.__doc__ = doc
        self.__container = Container(parent=container)
        # 取代当前实例.
        self.__container.set(MOSS, self)

        self.__importer: Importer = container.force_fetch(Importer)
        """ioc container"""
        self.__python_context: PyContext = PyContext()
        self.__buffer_print: BufferPrint = BufferPrint()

        self.__property_prompts: Dict[str, Optional[str]] = {}
        self.__property_docs: Dict[str, Optional[str]] = {}
        self.__property_implements: Dict[str, Optional[type]] = {}

        self.__local_types: Dict[str, type] = {}
        self.__local_type_names: Dict[type, str] = {}
        self.__local_type_prompts: Dict[str, str] = {}
        self.__local_type_implements: Dict[str, Optional[List[type]]] = {}
        self.__reserved_property_names: Set[str] = {'', }
        self.__reserved_locals_names: Set[str] = {'os', 'MoOS', 'print'}

        self.__bootstrapped = False

    def destroy(self) -> None:
        # 当前 container 也必须要销毁.
        self.__container.destroy()

        del self.__buffer_print
        del self.__container
        del self.__importer
        del self.__python_context

        del self.__property_docs
        del self.__property_implements
        del self.__property_prompts

        del self.__local_types
        del self.__local_type_names
        del self.__local_type_prompts

    def new(self, *named_vars, **variables) -> "MOSS":
        # 复制创造一个新的实例.
        os = BaseMOSS(doc=self.__doc__, container=self.__container)
        for var in named_vars:
            os.__add_any_var(value=var)
        for name, var in variables.items():
            os.__add_any_var(value=var, name=name)
        return os

    def define(
            self,
            name: str,
            value: Union[str, int, float, bool, Dict, List, ModelType],
            desc: Optional[str] = None,
    ) -> Any:
        model: Optional[Type[ModelType]] = None
        model_name = None
        typ = type(value)
        real_value = value
        if isinstance(value, ModelType):
            model = type(value)
            real_value = get_model_type_value(value)
        if model:
            model_name = self.add_type(typ=model)

        self.__python_context.defines[name] = Define(
            name=name,
            value=real_value,
            desc=desc,
            model_name=model_name,
        )
        self.print(f"> defined attr {name} to MoOS")
        return value

    def imports(self, module: str, *specs: str, **aliases: str) -> Dict[str, Any]:
        imports: List[Import] = []
        for spec in specs:
            imports.append(Import(
                module=module,
                spec=spec,
            ))
        for alias, spec in aliases.items():
            imports.append(Import(
                module=module,
                spec=spec,
                alias=alias,
            ))

        log = f"> from {module} import ("
        result = {}
        for imp in imports:
            v = self.__importer.imports(imp.module, imp.spec)
            alias = imp.alias
            spec = imp.spec
            name = alias if alias else spec
            if alias:
                log += f"{spec} as {alias},"
            else:
                log += f"{spec},"
            # self.set_attr(name=name, value=v)
            self.__python_context.imports[name] = imp
            result[name] = v
        log += ") # attach to MoOS"
        self.print(log)
        return result

    def print(self, *args, **kwargs) -> None:
        if self.__bootstrapped:
            return
        self.__buffer_print.print(*args, **kwargs)

    def flush(self) -> str:
        buffer = self.__buffer_print
        self.__buffer_print = BufferPrint()
        return buffer.buffer()

    def bootstrap(self) -> Dict[str, Any]:
        if not self.__bootstrapped:
            self.__bootstrapped = True
            self.__bootstrap_py_context()
        local_values: Dict[str, Any] = self.__local_types
        local_values['print'] = self.print
        local_values['os'] = self
        return local_values

    def update_context(self, context: PyContext) -> None:
        if self.__bootstrapped:
            raise RuntimeError("MoOS is already bootstrapped")
        self.__python_context.imports.update(context.imports)
        self.__python_context.defines.update(context.defines)

    def __bootstrap_py_context(self) -> None:
        for name in self.__python_context.imports:
            imp = self.__python_context.imports[name]
            value = self.__importer.imports(imp.module, imp.spec)
            desc = imp.description
            self.__add_any_var(value=value, name=name, desc=desc)

        for name in self.__python_context.defines:
            defined = self.__python_context.defines[name]
            real_value = defined.value
            if defined.model:
                model_type = self.__local_types[defined.model]
                real_value = new_model_from_value(model_type, defined.value)
            self.set_attr(
                real_value,
                name=name,
                doc=defined.desc,
                implements=None,
            )

    def __add_any_var(self, *, value: Any, name: Optional[str] = None, desc: Optional[str] = None) -> None:
        if isinstance(value, Var):
            if value.is_caller():
                self.add_method(
                    method=value.value(self.__container),
                    alias=name,
                    doc=value.desc(),
                    prompt=value.code_prompt(),
                )
            elif value.is_type():
                self.add_type(
                    typ=value.value(self.__container),
                    name=name,
                    prompt=value.code_prompt(),
                    doc=value.desc(),
                    implements=value.implements(),
                )
            else:
                self.set_attr(
                    value.value(self.__container),
                    name=name,
                    prompt=value.code_prompt(),
                    doc=value.desc(),
                    implements=value.implements(),
                )
        elif isinstance(value, AttrTypes):
            self.set_attr(value, name=name, doc=desc)
        elif isinstance(value, type):
            self.add_type(value, name=name, doc=desc)
        elif isinstance(value, Callable):
            self.add_method(method=value, alias=name, doc=desc)

    def dump_code_prompt(self) -> str:
        pass

    def dump_context(self) -> PyContext:
        py_context = self.__python_context.model_copy()
        for name in self.__python_context.defines:
            define = self.__python_context.defines[name]
            if hasattr(self, name):
                value = getattr(self, name)
                real_value = value
                if is_model_instance(value):
                    model = get_module_name(value)
                    if model:
                        define.model = model
                    real_value = get_model_type_value(value)
                # 重新定义 define 的 value 值.
                define.value = real_value
        return py_context

    def set_attr(
            self,
            value: AttrTypes,
            *,
            name: Optional[str] = None,
            implements: Optional[type] = None,
            prompt: Optional[str] = None,
            doc: Optional[str] = None,
    ) -> None:
        if not isinstance(value, AttrTypes):
            raise ValueError(f"value {value} is not of type {AttrTypes}")
        real_value = value
        # 如果是 provider.
        if isinstance(value, Provider):
            real_value = value.factory(self.__container)
            if not implements:
                implements = value.contract()

        if not name:
            if implements:
                name = implements.__name__
            else:
                name = real_value.__class__.__name__
            name = camel_to_snake(name)

        if implements:
            # 添加需要描述的类.
            self.add_type(implements)
        self.__set_raw_property(name=name, value=real_value, implements=implements, prompt=prompt)

    def add_type(
            self,
            typ: Type,
            *,
            name: Optional[str] = None,
            prompt: Optional[str] = None,
            doc: Optional[str] = None,
            implements: Optional[List[type]] = None,
    ) -> str:
        if inspect.isclass(typ):
            if not name:
                name = typ.__name__
            self.__add_raw_type(name=name, typ=typ, implements=implements, prompt=prompt)
        elif is_typing(typ):
            if not name:
                raise ValueError(f'type defines from typing must has name')
            if not prompt:
                prompt = f"{name} = {str(typ)}"
            self.__add_raw_type(name=name, typ=typ, implements=implements, prompt=prompt)
        else:
            raise TypeError(f"type must be an typing or a class, not {typ}")
        return name

    def add_method(
            self, *,
            method: Callable,
            alias: Optional[str] = None,
            doc: Optional[str] = None,
            prompt: Optional[str] = None,
    ) -> None:
        """
        添加一个方法.
        """
        if not is_caller(method):
            raise TypeError(f'method value {method} is not callable')
        name = alias
        if not name:
            name = method.__name__
        self.__set_raw_property(name=name, value=method, implements=None, prompt=prompt)

    def __set_raw_property(
            self,
            *,
            name: str,
            value: Any,
            doc: Optional[str] = None,
            implements: Optional[type] = None,
            prompt: Optional[str] = None,
    ) -> None:
        if name.startswith("_"):
            raise NameError(f"name must not start with '_'")
        if name in self.__reserved_property_names:
            raise NameError(f'name {name} is reserved')
        # 允许替换掉原来的.
        setattr(self, name, value)
        self.__property_implements[name] = implements
        self.__property_prompts[name] = prompt
        self.__property_docs[name] = doc

    def __add_raw_type(
            self,
            *,
            name: str,
            typ: Type,
            implements: Optional[type] = None,
            prompt: Optional[str] = None,
    ) -> None:
        if name in self.__reserved_locals_names:
            raise NameError(f'{name} is reserved for MoOS')
        if typ in self.__local_type_names:
            # only register once
            name = self.__local_type_names[typ]
        else:
            self.__local_type_names[typ] = name
        self.__local_type_prompts[name] = prompt
        self.__local_type_implements[name] = implements

    def __get_typehint(self, implement: Type) -> str:
        typehint = self.__local_type_names.get(implement, None)
        if not typehint:
            typehint = str(implement)
        return typehint
