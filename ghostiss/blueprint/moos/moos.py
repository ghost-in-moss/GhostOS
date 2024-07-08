from typing import List, Set, Dict, Any, Optional, Union, TypedDict, Iterable, Type, Callable
from abc import ABC, abstractmethod
import re
import inspect
from contextlib import redirect_stdout
from pydantic import BaseModel
from importlib.abc import MetaPathFinder
from ghostiss.container import Container, CONTRACT
from ghostiss.blueprint.moos.variable import Var, VarKind, Descriptive, ClassVar, ModelType, lib
from ghostiss.blueprint.moos.context import PyContext, Define, Import
from ghostiss.blueprint.moos.importer import Importer
from ghostiss.helpers import camel_to_snake
from ghostiss.container import Provider
from ghostiss.blueprint.moos.helpers import (
    is_caller, get_callable_definition, get_attr_prompt, get_description,
    get_module_name,
    is_model_instance,
    is_typing,
    is_model_class, get_model_type_value, new_model_from_value,
)
from ghostiss.helpers import BufferPrint

AttrTypes = Union[int, float, str, bool, list, dict, None, Provider, ModelType]


class LaMOS(ABC):
    """
    language Model-oriented Operating System
    full python code interface for large language models
    """

    # --- 创建 MoOS 的方法 --- #

    @abstractmethod
    def new(self, *named_vars, **variables) -> "LaMOS":
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
    ):
        """
        add a method to LaMOS
        :param doc:
        :param method:
        :param alias:
        :param prompt:
        :return:
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


class BaseLaMOS(LaMOS):

    def __init__(self, *, doc: str, container: Container):
        self.__doc__ = doc
        self.__container = container
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
        self.__reserved_type_names: Set[str] = {'os', 'LaMOS'}

        self.__bootstrapped = False

    def destroy(self) -> None:
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
        self.print(f"> defined attr {name} to LaMOS")
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
        log += ") # attach to LaMOS"
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

    def new(self, *named_vars, **variables) -> "LaMOS":
        pass

    def update_context(self, context: PyContext) -> None:
        if self.__bootstrapped:
            raise RuntimeError("LaMOS is already bootstrapped")
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

        # name = alias
        # if not prompt:
        #     prompt = get_class_prompt(cls=typ, name=name, doc=doc, methods=methods, init=init, attrs=attrs)
        #     if module is None:
        #         module = typ.__module__
        #     if module_spec is None:
        #         module_spec = typ.__name__
        # # add comment to type
        # comment = f"# from {module} import {module_spec}"
        # if name != module_spec:
        #     comment += f" as {name}"
        # if implements:
        #     typehints = []
        #     for imp in implements:
        #         typehint = self.__get_typehint(imp)
        #         typehints.append(typehint)
        #     comment += f"\n implements {', '.join(typehints)}"
        # prompt = comment + "\n" + prompt
        # self.__add_raw_type(name, typ, prompt)

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
            doc: Optional[str] = None,
            implements: Optional[type] = None,
            prompt: Optional[str] = None,
    ) -> None:
        if name in self.__reserved_type_names:
            raise NameError(f'{name} is reserved for LaMOS')
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

# class BasicLaMOS(LaMOS):
#
#     def __init__(self, *, doc: str, container: Container):
#         self.__doc__ = doc
#         self.__container = container
#         """ioc container"""
#         self.__python_context: PyContext = PyContext()
#         """默认的 py context """
#         # self.__loaded_variables: Dict[str, Var] = {}
#         # self.__duplicated_name_idx = duplicated_name_idx
#         self.__local_types: Dict[type, str] = {}
#         self.__local_types_order: List[str] = []
#         self.__local_type_vars: Dict[str, Var] = {}
#         self.__local_type_prompts: Dict[str, str] = {}
#         self.__model_types: Dict[str, type] = {}
#
#         self.__mos_attrs: Dict[str, Var] = {}
#         self.__mos_attrs_order: List[str] = []
#         self.__mos_attr_prompts: Dict[str, str] = {}
#
#     def __add_type_var(self, name: str, var: Var) -> None:
#         """
#         添加一个本地变量.
#         """
#         kind = var.kind()
#         if not kind.is_type():
#             # 只添加 type.
#             return
#
#         if kind.is_contract_type():
#             # 如果是 container 的 contract, 则需要从 container 中生成实例然后绑定.
#             self.__add_contract_type(name, var)
#         elif kind.is_model_type():
#             # 如果是 model 类型的 type,
#             self.__add_model_type(name, var)
#         elif kind.is_type():
#             self.__add_local_type(name, var)
#
#     def __add_attr_var(self, name: str, var: Var) -> None:
#         """
#         添加一个属性到 moos 上.
#         """
#         kind = var.kind()
#         if not kind.is_attr():
#             return
#         elif kind.is_lib():
#             self.__add_lib_attr(name, var)
#         else:
#             self.__add_property(name, var)
#
#     def __add_caller_attr(self, name: str, var: Var) -> None:
#         """
#         添加一个 caller 到 moos 上.
#         """
#         caller = self.__add_raw_property(name, var)
#         if not isinstance(caller, Callable):
#             raise ValueError(f"{caller} is not callable")
#         # caller 的 prompt 机制不同.
#         prompt = self.__get_caller_prompt(name, var)
#         self.__mos_attr_prompts[name] = prompt
#
#     def __add_model_type(self, name: str, var: Var) -> None:
#         t = self.__add_local_type(name, var)
#         # 注册 model 的类型, 方便后续查找.
#         import_from = var.import_from()
#         if import_from:
#             self.__model_types[import_from] = t
#
#     def __add_local_type(self, name: str, var: Var) -> type:
#         if name in self.__local_type_vars:
#             # 不解决重名问题.
#             raise NameError(f"duplicate type name {name}")
#         v = var.value(self.__container)
#         if not isinstance(v, type):
#             # 不注册非类型.
#             raise ValueError(f"type {v} not supported as a type")
#         if v in self.__local_types:
#             # 强制要求一个 type 只注册一次.
#             raise ValueError(f"duplicate type {v}")
#
#         self.__local_types[v] = name
#         self.__local_types_order.append(name)
#         self.__local_type_vars[name] = var
#
#         # 解决 prompt 的问题. 解决办法是通用的.
#         prompt = self.__get_type_prompt(name, var)
#         self.__local_type_prompts[name] = prompt
#         return v
#
#     def __add_contract_type(self, name: str, var: Var) -> None:
#         v = self.__add_local_type(name, var)
#         ins = self.__container.force_fetch(v)
#         attr_name = camel_to_snake(name)
#         self.__add_lib_attr(attr_name, lib(val=ins, contract=v))
#
#     def __add_lib_attr(self, name: str, var: Var) -> None:
#         v = self.__add_raw_property(name, var)
#         # 准备 prompt.
#         contract = var.implements()
#         if contract is None:
#             contract = type(v)
#         doc = var.desc()
#         type_hint = self.__get_implement_type_hint(contract)
#         prompt = get_attr_prompt(name, type_hint, doc)
#         self.__mos_attr_prompts[name] = prompt
#
#     def __get_implement_type_hint(self, contract: Optional[Type]) -> Optional[str]:
#         """
#         返回类型约束. 类型约束有可能是
#         """
#         if contract is None:
#             return None
#         if contract in {str, bool, int, float}:
#             # 支持标量.
#             return str(contract)
#         type_hint = self.__local_types.get(contract, None)
#         if type_hint:
#             type_hint = '"' + str(contract) + '"'
#         return type_hint
#
#     def __add_property(self, name: str, var: Var) -> None:
#         v = self.__add_raw_property(name, var)
#
#     def __add_raw_property(self, name: str, var: Var) -> Any:
#         if name in self.__mos_attrs:
#             raise NameError(f"duplicate property name {name}")
#         self.__mos_attrs[name] = var
#         v = var.value(self.__container)
#         setattr(self, name, v)
#         return v
#
#         # types
#         # self.__registered_types: Dict[type, Var] = {}
#         # self.__descriptive_types: Dict[type, Var] = {}
#         # self.__name_to_types: Dict[str, Var] = {}
#
#         # 对自身状态的描述.
#
#         # self.__libraries: Dict[str, Var] = {}
#         # """绑定到 moos 上的 library 库, 对外只展示 interface. """
#         #
#         # self.__local_callers: Dict[str, Var] = {}
#         # """本地展示的类型, 包括类和方法."""
#         #
#         # self.__local_types: Dict[type, Optional[Var]] = {}
#         # """各种要独立展示的类型, 和这些类型对外展示的名字. """
#         #
#         # self.__raw_attrs: Dict[str, Var] = {}
#         # """添加到上下文中的 property. """
#         #
#         # self.__type_dict_attrs: Dict[str, Dict[str, Var]] = {}
#         # """相同类型的 value 以 dict 形式注册的 attr."""
#         #
#         # self.__attr_orders: List[str] = []
#         # """属性的顺序列表. 和加载顺序有关. """
#         #
#         # self.__attr_names: Set[str] = set()
#         # """已经存在的名字. 用来排除冲突."""
#         #
#         # self.__property_prompts: Dict[str, str] = {}
#         # """每一个 property 对应的 code prompt """
#     #
#     # def new(self, local_values: Dict[str, Any]) -> "LaMOS":
#     #     for key, val in local_values.items():
#     #         if isinstance(val, Var):
#     #             self.__add_local_var(key, val)
#     #         elif isinstance(val, type):
#     #             self.__add_local_type(key, val)
#     #         elif is_caller(val):
#     #             self.__add_caller(key, val)
#     #         else:
#     #             self.__add_local_value(key, val)
#     #     return self
#     #
#     # def __add_local_type(self, name: str, value: type) -> None:
#     #     if isinstance(value, ModelType):
#     #         self.__add_local_var(name, model_var(value))
#     #
#     #
#     #
#     #
#     # def __add_local_var(self, key: str, val: Var) -> None:
#     #     pass
#     #
#     # def update_variables(self, variables: Iterable[Var]) -> None:
#     #     for var in variables:
#     #         self.__add_var(var)
#     #
#     # def update_context(self, context: PyContext) -> None:
#     #     pass
#     #
#     # def define(self, name: str, value: Union[str, int, float, bool, Dict, List, BaseModel], desc: str) -> Any:
#     #     define = Define(name=name, value=value, desc=desc)
#     #     if isinstance(value, BaseModel) or isinstance(value, TypedDict):
#     #         model = type(value)
#     #         type_name = self.__add_type(model)
#     #         define.model = type_name
#     #     self.__python_context.add_var(define)
#     #     # todo: var
#     #     self.__bind_property()
#     #     return value
#     #
#     # def dump_locals(self) -> Dict[str, Any]:
#     #     pass
#     #
#     # def dump_context(self) -> PyContext:
#     #     pass
#     #
#     # def dump_code_prompt(self) -> str:
#     #     pass
#     #
#     # def __add_type(self, var: Var) -> Var:
#     #     kind = var.kind()
#     #     if VarKind.LIBRARY == kind:
#     #         return var
#     #     elif VarKind.VALUE == kind:
#     #         return var
#     #     elif VarKind.CLASS == kind:
#     #         t = var.value(self.__container)
#     #         name = var.name()
#     #         if name in self.__name_to_types:
#     #             name = self.__reassign_var_name(name)
#     #             var = var.with_name(name)
#     #         if t in self.__registered_types:
#     #
#     #     elif VarKind.CALLER == kind:
#     #         v = var.value(self.__container)
#     #         self.__local_callers[v] =
#     #     elif VarKind.ABSTRACT == kind:
#     #         pass
#     #     elif VarKind.MODEL == kind:
#     #         pass
#     #     else:
#     #         raise ValueError(f"unknown kind of var: {var}")
#     #
#     #
#     # def __add_var(self, var: Var) -> None:
#     #     kind = var.kind()
#     #     if VarKind.LIBRARY == kind:
#     #         self.__add_lib(var)
#     #     elif VarKind.CLASS == kind:
#     #         self.__add_class(var)
#     #     elif VarKind.VALUE == kind:
#     #         self.__add_value(var)
#     #     elif VarKind.CALLER == kind:
#     #         pass
#     #     elif VarKind.ABSTRACT == kind:
#     #         pass
#     #     elif VarKind.MODEL == kind:
#     #         pass
#     #     else:
#     #         raise ValueError(f"unknown kind of var: {var}")
#     #
#     # def __bind_defaults(self) -> None:
#     #     pass
#     #
#     # def __add_type(self, typ: type) -> str:
#     #     pass
#     #
#     # def __bind_property(self, var: Var) -> None:
#     #     """
#     #     绑定一个变量.
#     #     """
#     #
#     #
