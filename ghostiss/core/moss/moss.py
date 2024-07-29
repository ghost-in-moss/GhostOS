from __future__ import annotations
import inspect
import typing
from typing import List, Set, Dict, Any, Optional, Union, Tuple, Type, TypedDict
from types import ModuleType
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from ghostiss.container import Container, CONTRACT
from ghostiss.core.moss.context import PyContext, Variable, Imported
from ghostiss.core.moss.modules import Modules
from ghostiss.reflect import (
    Importing,
    reflect, reflects,
    Reflection, TypeReflection,
    Model, ModelType, ModelObject,
    Attr, Method, ClassPrompter, Locals, Library,
    get_typehint_string,
    get_model_object_meta, new_model_instance
)
from ghostiss.helpers import camel_to_snake
from ghostiss.container import Provider
from ghostiss.helpers import BufferPrint
from ghostiss.core.messages.message import MessageType

AttrTypes = Union[int, float, str, bool, list, dict, None, Provider, ModelType]


class System(ABC):

    @abstractmethod
    def imports(self, module: str, *specs: str, **aliases: str) -> Dict[str, Any]:
        """
        replace from ... import ... as ...
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
        replace builtin print, output will add to next message.
        """
        pass


class MOSS(System, ABC):
    """
    language Model-oriented Operating System Simulation
    full python code interface for large language models
    """

    # --- 创建 MOSS 的方法 --- #

    @abstractmethod
    def new(self, *named_vars, **variables) -> "MOSS":
        """
        return a new instance
        """
        pass

    @abstractmethod
    def with_vars(self, *named_vars, **variables) -> "MOSS":
        pass

    @abstractmethod
    def update_context(self, context: PyContext) -> "MOSS":
        """
        为 MOSS 添加更多的变量, 可以覆盖掉之前的.
        :param context:
        :return:
        """
        pass

    # --- MOSS 默认暴露的基础方法 --- #

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
    def dump_locals(self) -> Dict[str, Any]:
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

        class MOSS(ABC):
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
            *,
            code: str,
            target: str = "",
            args: Optional[List[str]] = None,
            kwargs: Optional[Dict[str, str]] = None,
            update_locals: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        基于 moos 提供的上下文, 运行一段代码.
        :param code: 需要运行的代码.
        :param target: 指定一个变量名用来获取返回值. 如果为空, 则返回 None. 如果是一个方法, 则会运行它.
        :param args: 如果 args 不为 None, 则认为 target 是一个函数, 并从 locals 里指定参数
        :param kwargs: 类似 args
        :param update_locals: 额外添加到上下文里的 locals 变量. 但这些变量不会生成 code prompt.
        :return: 根据 result_name 从 code 中获取返回值.
        :exception: any exception will be raised, handle them outside
        """
        local_values = self.dump_locals()
        if update_locals is not None:
            local_values.update(update_locals)
        if target and target not in local_values:
            # 对 result_name 做初始化.
            local_values[target] = None
        local_values['print'] = self.print
        local_values['os'] = self
        # 执行代码. 注意!! 暂时没有考虑任何安全性问题. 理论上应该全部封死.
        # 考虑使用 RestrictPython
        temp = ModuleType("moss")
        for key, attr in local_values.items():
            setattr(temp, key, attr)

        compiled = compile(code, filename='<MOSS>', mode='exec')
        # use compile() can found some error at compile stage, and compile() provides the flexibility by pass the 'mode'
        # If exec gets two separate objects as globals and locals,
        # the code will be executed as if it were embedded in a class definition.
        exec(compiled, temp.__dict__)
        # the second positional arguments of exec() is global named space (it storages global variables)

        if (args is not None or kwargs is not None) and target is not None:
            caller = getattr(temp, target)
            if not inspect.isfunction(caller):
                raise TypeError(f"target {target} is not callable")
            real_args = []
            real_kwargs = {}
            if args:
                for origin in args:
                    arg_val = getattr(temp, origin)
                    real_args.append(arg_val)
            if kwargs:
                for key, origin in kwargs.items():
                    real_kwargs[key] = getattr(temp, origin)
            return caller(*real_args, **real_kwargs)  # execute the main method when target is 'main'

        if target:
            return getattr(temp, target)
        return None


class BasicMOSSImpl(MOSS):
    """
    MOSS 的基础实现.
    """

    def __init__(self, *, container: Container, doc: str = "", pycontext: Optional[PyContext] = None):
        # 重定义自身的 doc.
        if doc:
            self.__doc__ = doc
        else:
            self.__doc__ = MOSS.__doc__

        self.__container = Container(parent=container)
        """封装一个 MOSS 独立的容器. 这个容器会重新绑定 MOSS"""
        self.__container.set(MOSS, self)

        self.__modules: Modules = container.force_fetch(Modules)
        """MOSS 默认使用的 modules, 用来代理 import 相关的逻辑."""

        self.__python_context: PyContext = pycontext if pycontext else PyContext()
        """实例话一个 pycontext 容器. 存储可持久化的引用和变量."""

        self.__buffer_print: BufferPrint = BufferPrint()
        """代理 print 的方法."""

        self.__reserved_locals_names: Set[str] = {
            'os', 'MOOS', 'print', 'imports', 'define',
        }
        """限制使用的关键字"""

        self.__reflections: Dict[str, Reflection] = {}
        """建立一个 reflection 的字典, 方便按变量名查找."""

        self.__reflection_names: List[str] = []
        """所有 reflection 的变量名. 定义为数组方便保留顺序."""

        self.__attrs: Dict[str, Attr] = {}
        """属性类的变量, 会挂载到 moss 上. """

        self.__methods: Dict[str, Method] = {}
        """方法类的变量, 也会挂载到 moss 上."""
        self.__imported: List[Importing] = []
        """通过 from ... import ... 展示的变量. 它们没有特殊的 prompt, 预计是 llm 已经掌握的公共库. """

        self.__context_types: Dict[str, TypeReflection] = {}
        """上下文中需要展示的各种类型, 这些类型会独立于 moss 外部, 作为类型定义可以使用."""

        self.__context_type_names: Dict[type, str] = {}
        """建立一个反向字典, 通过类型查找它在上下文中的变量名. """

        self.__reassign_name_idx: int = 1
        """建立一个重命名索引. 当变量在上下文中出现重名时, 会粗暴地给它添加一个整数的后缀."""

        self.__bootstrapped = False
        """ MOSS 是否已经初始化. 一旦初始化了, 就无法再引入变量, 需要重新 new. """

        self.__context_prompter: Optional[Locals] = None
        """ 用来将所有上下文生成 prompt 的对象. 本身也是一个 reflection"""

        self.__context_values: Optional[Dict[str, Any]] = None
        """ 持有上下文中所有的变量. 只有在 bootstrap 之后才会加载. """

    def destroy(self) -> None:
        """
        防止互相持有, 需要提供一个 destroy 方法.
        """
        # 当前 container 也必须要销毁.
        self.__container.destroy()

        del self.__buffer_print
        del self.__container
        del self.__modules
        del self.__python_context

        del self.__attrs
        del self.__methods
        del self.__reflections
        del self.__reflection_names

        del self.__context_types
        del self.__context_type_names

        del self.__context_prompter
        del self.__context_values

    @staticmethod
    def _default_kwargs() -> Dict[str, Any]:
        """
        MOSS 默认要引用的上下文变量.
        """
        # 目前将最通用的一些类型直接引入.
        return {
            'typing': Importing(value=typing, module='typing'),
            'BaseModel': Importing(value=BaseModel, module='pydantic'),
            'Field': Importing(value=Field, module='pydantic'),
            'TypedDict': Importing(value=TypedDict, module='typing'),
            'ABC': Importing(value=ABC),
            'abstractmethod': Importing(value=abstractmethod),
            # reflect 方法会自动将它变成 Typing 类型反射.
            'MessageType': MessageType,
        }

    def new(self, *named_vars, **variables) -> "MOSS":
        """
        初始化一个 MOSS.
        :param named_vars: 每个元素需要拥有 __name__ , 比如一个 class. 也可以是 Provider.
        :param variables: name => value 的方式传入.
        """
        # 复制创造一个新的实例.
        os = BasicMOSSImpl(doc=self.__doc__, container=self.__container.parent)
        kwargs = self._default_kwargs()
        kwargs.update(variables)
        return os.with_vars(*named_vars, **kwargs)

    def with_vars(self, *named_vars, **variables) -> "MOSS":
        """
        为 MOSS 添加变量, 变量会自动反射
        :param named_vars: 每个元素需要拥有 __name__, 比如一个 class. 也可以是 Provider.
        :param variables: 每个元素都有 alias => value. value 可以是 Reflection, Provider, 和其它任意元素.
        :return:
        """
        args = []
        for arg in named_vars:
            if isinstance(arg, Provider):
                self.__add_provider(arg, None)
            else:
                args.append(arg)
        kwargs = {}
        for name, arg in variables.items():
            if isinstance(arg, Provider):
                self.__add_provider(arg, name)
            else:
                kwargs[name] = arg
        reflections = reflects(*args, **variables)
        for r in reflections:
            self.add_reflection(r)
        return self

    def __add_provider(self, provider: Provider, name: Optional[str]) -> None:
        """
        Provider 可以直接添加到 MOSS, 会动态从容器中生成一个数据.
        :param provider: 工厂方法.
        :param name: 重命名的名字.
        :return:
        """
        contract = provider.contract()
        impl = provider.factory(self.__container)

        contract_reflect = Library(cls=contract, alias=name)
        attr = Attr(value=impl, name=camel_to_snake(contract_reflect.name()))
        self.__add_type(contract_reflect)
        self.__add_attr(attr)

    def add_reflection(self, reflection: Reflection, reassign_name: bool = True) -> None:
        """
        将一个反射添加到上下文里.
        :param reflection: 反射.
        :param reassign_name: 如果重名的话, 是否要对这个反射重命名.
        """
        name = reflection.name()
        # 引用的变量名不能是保留字里的.
        if name in self.__reserved_locals_names or name in self.__reflections:
            if reassign_name:
                name = self.__reassign_name(name, set(self.__reflections.keys()))
                reflection.update(name=name)
            else:
                raise NameError(f'{name} already defined')
        self.__reflections[name] = reflection
        self.__reflection_names.append(name)

        # 正式添加.
        if isinstance(reflection, Importing):
            self.__imported.append(reflection)
        elif isinstance(reflection, Attr):
            self.__add_attr(reflection)
        elif isinstance(reflection, Method):
            self.__add_method(reflection)
        elif isinstance(reflection, TypeReflection):
            # 如果是 type reflection 类型, 上下文中它可能已经存在了.
            typ = reflection.value()
            if typ in self.__context_type_names:
                # 不重复添加类型. 所有类型使用第一个定义的.
                return
            self.__add_type(reflection)

            # 默认判断是否要添加 lib.
            impl = self.__container.get(typ)
            if impl:
                lib = Attr(value=impl, typehint=typ, name=camel_to_snake(reflection.name()))
                self.add_reflection(lib, reassign_name=True)
        else:
            raise AttributeError(f"{reflection} not supported yet")

        # 递归地添加 typehint 到上下文里.
        typehint = reflection.typehint()
        if typehint is not None:
            reflection = reflect(var=typehint)
            self.add_reflection(reflection)

    def __add_type(self, reflection: TypeReflection) -> None:
        """
        添加一个 type reflection.
        """
        self.__context_types[reflection.name()] = reflection
        self.__context_type_names[reflection.value()] = reflection.name()

    def __add_attr(self, attr: Attr) -> None:
        """
        添加一个属性, 会加到 moss 的属性上.
        尽量不作为 moss 外部的局部变量, 因为无法用 python 语言清晰定义一个局部变量.

        python 语法定义变量: a: type = value
        而 class 的属性:
        class Foo
            a: type

        可以省略赋值逻辑, 然后通过 observe 方法让 LLM 去查看值.
        """
        self.__attrs[attr.name()] = attr
        self.__dict__[attr.name()] = attr.value()

    def __add_method(self, method: Method) -> None:
        self.__methods[method.name()] = method
        self.__dict__[method.name()] = method.value()

    def define(
            self,
            name: str,
            value: Union[str, int, float, bool, Dict, List, ModelObject],
            desc: Optional[str] = None,
    ) -> Any:
        defined_value = value
        model_name: Optional[str] = None
        if isinstance(value, ModelObject):
            defined_value = get_model_object_meta(value)
            typehint = type(value)
            model_name = self.__context_type_names.get(typehint)
            if not typehint:
                self.add_reflection(Model(model=typehint), reassign_name=True)
                model_name = self.__context_type_names.get(typehint, typehint.__name__)

        d = Variable(
            name=name,
            value=defined_value,
            desc=desc,
            model_name=model_name,
        )
        self.__python_context.add_define(d)
        self.print(f"> defined attr {name} to MOSS")
        return value

    def imports(self, module: str, *specs: str, **aliases: str) -> Dict[str, Any]:
        imports: List[Imported] = []
        for spec in specs:
            imports.append(Imported(
                module=module,
                spec=spec,
            ))
        for alias, spec in aliases.items():
            imports.append(Imported(
                module=module,
                spec=spec,
                alias=alias,
            ))

        log = f"> from {module} import ("
        result: Dict[str, Any] = {}
        for imp in imports:
            v = self.__modules.imports(imp.module, imp.spec)
            alias = imp.alias
            spec = imp.spec
            name = alias if alias else spec
            if alias:
                log += f"{spec} as {alias},"
            else:
                log += f"{spec},"
            # 关键: 所有的 import 动作会将引用添加到 pycontext 里, 下轮时默认携带.
            self.__python_context.add_import(imp)
            result[name] = v
        log += ") # attach to MOSS"
        self.print(log)
        return result

    def print(self, *args, **kwargs) -> None:
        if not self.__bootstrapped:
            raise RuntimeError("print is prepared after moss bootstrapping")
        self.__buffer_print.print(*args, **kwargs)

    def flush(self) -> str:
        buffer = self.__buffer_print
        self.__buffer_print = BufferPrint()
        return buffer.buffer()

    def dump_locals(self) -> Dict[str, Any]:
        self.__bootstrap()
        return self.__context_values

    def __bootstrap(self) -> None:
        if self.__bootstrapped:
            return
        self.__bootstrapped = True
        self.__bootstrap_py_context()

        # values
        local_values: Dict[str, Any] = {}
        for imp in self.__imported:
            local_values[imp.name()] = imp.value()
        for key, reflection in self.__context_types.items():
            local_values[key] = reflection.value()

        # prompt
        attrs, methods = self.__get_defined_attrs_and_methods()
        for attr in attrs:
            self.__update_typehint_and_extends(attr)
        for method in methods:
            self.__update_typehint_and_extends(method)

        methods.append(
            Method(caller=System.imports)
        )
        local_types: List[TypeReflection] = []
        for name in self.__reflection_names:
            if name in self.__context_types:
                local_types.append(self.__context_types[name])

        moss = ClassPrompter(
            cls=System,
            alias="MOSS",
            doc=MOSS.__doc__,
            attrs=attrs,
            methods=methods,
        )
        local_types.append(moss)
        local_prompter = Locals(
            methods=[],
            types=local_types,
            imported=self.__imported,
        )

        local_values['print'] = self.print
        local_values['os'] = self
        local_values['MOSS'] = moss.value()
        self.__context_values = local_values
        self.__context_prompter = local_prompter

    def __get_defined_attrs_and_methods(self) -> Tuple[List[Attr], List[Method]]:
        attrs = []
        methods = []
        for name in self.__reflection_names:
            if name in self.__attrs:
                attrs.append(self.__attrs[name])
            elif name in self.__methods:
                methods.append(self.__methods[name])
        return attrs, methods

    def dump_code_prompt(self) -> str:
        self.__bootstrap()
        return self.__context_prompter.prompt()

    def __update_typehint_and_extends(self, r: Reflection) -> Reflection:
        """
        根据上下文更新 typehint 的讯息, 主要是有可能重名.
        """
        typehint = r.typehint()
        if typehint is not None:
            typehint = self.__get_typehint(typehint)
        extends = r.extends()
        new_extends = []
        if extends:
            for ext in extends:
                ext_typehint = self.__get_typehint(ext)
                new_extends.append(ext_typehint)
        r = r.update(typehint=typehint, extends=new_extends)
        return r

    def update_context(self, context: PyContext) -> "MOSS":
        if self.__bootstrapped:
            raise RuntimeError("MOSS is already bootstrapped")
        self.__python_context = self.__python_context.join(context)
        return self

    def __bootstrap_py_context(self) -> None:
        """
        初始化 MOSS 的 py context, 将里面的引用和变量添加到上下文.
        """
        # 解决引用.
        for imp in self.__python_context.imported:
            name = imp.get_name()
            value = self.__modules.imports(imp.module, imp.spec)
            r = reflect(var=value, name=name)
            self.add_reflection(r, reassign_name=False)

        # 解决变量.
        for defined in self.__python_context.variables:
            name = defined.name
            real_value = defined.value
            if defined.model:
                model_type = self.__context_types.get(defined.model, None)
                if model_type is None:
                    raise AttributeError(f"{defined.model} not found")
                real_value = new_model_instance(model_type, defined.value)
            r = Attr(name=name, value=real_value)
            self.add_reflection(r, reassign_name=False)

    def dump_context(self) -> PyContext:
        defines = []
        for define in self.__python_context.variables:
            name = define.name
            if name in self.__dict__:
                value = self.__dict__[name]
                if define.model:
                    value = get_model_object_meta(value)
                define.value = value
            defines.append(define)
        self.__python_context.variables = defines
        return self.__python_context.model_copy(deep=True)

    def __get_typehint(self, typehint: Any) -> str:
        """
        根据 typehint 类型, 从上下文中获取它的变量名.
        这个方法是因为有些引用的 类型, 在上下文中被重命名了. 比如 from pydantic import BaseModel as Model
        这样描述类型关系需要再次查找重命名.
        todo: 希望未来用 tree-sitter 等类库有更好的实现.
        """
        if not typehint:
            return ""
        typehint = self.__context_type_names.get(typehint, None)
        if not typehint:
            typehint = get_typehint_string(typehint)
        return typehint

    def __reassign_name(self, name: str, names: Set[str]) -> str:
        """
        对重名的变量进行粗暴地重命名.
        """
        if name in names:
            new_name = f"{name}.{self.__reassign_name_idx}"
            self.__reassign_name_idx += 1
            if new_name in names:
                return self.__reassign_name(name, names)
            return new_name
        return name


class TestMOSSProvider(Provider):
    """
    添加一个默认的 MOSS 实现.
    方便单元测试.
    """

    def singleton(self) -> bool:
        return False

    def contract(self) -> Type[CONTRACT]:
        return MOSS

    def factory(self, con: Container) -> Optional[CONTRACT]:
        return BasicMOSSImpl(
            doc="",
            container=con,
        )
