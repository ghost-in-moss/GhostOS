import inspect
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
        replace builtin print
        """
        pass


class MOSS(System, ABC):
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
    def with_vars(self, *named_vars, **variables) -> "MOSS":
        pass

    @abstractmethod
    def update_context(self, context: PyContext) -> "MOSS":
        """
        为 MoOS 添加更多的变量, 可以覆盖掉之前的.
        :param context:
        :return:
        """
        pass

    # --- MoOS 默认暴露的基础方法 --- #

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

    def __init__(self, *, container: Container, doc: str = ""):
        if doc:
            self.__doc__ = doc
        else:
            self.__doc__ = MOSS.__doc__
        self.__container = Container(parent=container)
        # 取代当前实例.
        self.__container.set(MOSS, self)

        self.__importer: Modules = container.force_fetch(Modules)
        """ioc container"""
        self.__python_context: PyContext = PyContext()
        self.__buffer_print: BufferPrint = BufferPrint()

        self.__reserved_locals_names: Set[str] = {
            'os', 'MOOS', 'print', 'imports', 'define',
        }

        self.__reflections: Dict[str, Reflection] = {}
        self.__reflection_names: List[str] = []
        self.__attrs: Dict[str, Attr] = {}
        self.__methods: Dict[str, Method] = {}
        self.__local_types: Dict[str, TypeReflection] = {}
        self.__local_type_names: Dict[type, str] = {}
        self.__imported: List[Importing] = []

        self.__reassign_name_idx: int = 1

        self.__bootstrapped = False
        self.__local_prompter: Optional[Locals] = None
        self.__local_values: Optional[Dict[str, Any]] = None

    def destroy(self) -> None:
        # 当前 container 也必须要销毁.
        self.__container.destroy()

        del self.__buffer_print
        del self.__container
        del self.__importer
        del self.__python_context

        del self.__attrs
        del self.__methods
        del self.__reflections
        del self.__reflection_names

        del self.__local_types
        del self.__local_type_names

        del self.__local_prompter
        del self.__local_values

    def _default_kwargs(self) -> Dict[str, Any]:
        return {
            'BaseModel': Importing(value=BaseModel, module='pydantic'),
            'Field': Importing(value=Field, module='pydantic'),
            'TypedDict': Importing(value=TypedDict, module='typing'),
            'ABC': Importing(value=ABC),
            'abstractmethod': Importing(value=abstractmethod),
        }

    def new(self, *named_vars, **variables) -> "MOSS":
        # 复制创造一个新的实例.
        os = BasicMOSSImpl(doc=self.__doc__, container=self.__container.parent)
        return os.with_vars(*named_vars, **variables)

    def with_vars(self, *named_vars, **variables) -> "MOSS":
        args = []
        kwargs = self._default_kwargs()
        for arg in named_vars:
            if isinstance(arg, Provider):
                self.__add_provider(arg, None)
            else:
                args.append(arg)
        for name, arg in variables.items():
            if isinstance(arg, Provider):
                self.__add_provider(arg, name)
            else:
                kwargs[name] = arg
        reflections = reflects(*args, **kwargs)
        for r in reflections:
            self.add_reflection(r)
        return self

    def __add_provider(self, provider: Provider, name: Optional[str]) -> None:
        contract = provider.contract()
        impl = provider.factory(self.__container)

        contract_reflect = Library(cls=contract, alias=name)
        attr = Attr(value=impl, name=camel_to_snake(contract_reflect.name()))
        self.__add_type(contract_reflect)
        self.__add_attr(attr)

    def add_reflection(self, reflection: Reflection, reassign_name: bool = False) -> None:
        name = reflection.name()
        if name in self.__reserved_locals_names:
            raise NameError(f"'{name}' is reserved name")
        if name in self.__reflections:
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
            typ = reflection.value()
            if typ in self.__local_type_names:
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

    def __add_type(self, reflection: TypeReflection) -> None:
        self.__local_types[reflection.name()] = reflection
        self.__local_type_names[reflection.value()] = reflection.name()

    def __add_attr(self, attr: Attr) -> None:
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
            model_name = self.__local_type_names.get(typehint)
            if not typehint:
                self.add_reflection(Model(model=typehint), reassign_name=True)
                model_name = self.__local_type_names.get(typehint, typehint.__name__)

        d = Variable(
            name=name,
            value=defined_value,
            desc=desc,
            model_name=model_name,
        )
        self.__python_context.add_define(d)
        self.print(f"> defined attr {name} to MoOS")
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
            v = self.__importer.imports(imp.module, imp.spec)
            alias = imp.alias
            spec = imp.spec
            name = alias if alias else spec
            if alias:
                log += f"{spec} as {alias},"
            else:
                log += f"{spec},"
            self.__python_context.add_import(imp)
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

    def dump_locals(self) -> Dict[str, Any]:
        self.__bootstrap()
        return self.__local_values

    def __bootstrap(self) -> None:
        if self.__bootstrapped:
            return
        self.__bootstrapped = True
        self.__bootstrap_py_context()

        # values
        local_values: Dict[str, Any] = {}
        for imp in self.__imported:
            local_values[imp.name()] = imp.value()
        for key, reflection in self.__local_types.items():
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
            if name in self.__local_types:
                local_types.append(self.__local_types[name])

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
        self.__local_values = local_values
        self.__local_prompter = local_prompter

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
        return self.__local_prompter.prompt()

    def __update_typehint_and_extends(self, r: Reflection) -> Reflection:
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
            raise RuntimeError("MoOS is already bootstrapped")
        self.__python_context.join(context)
        return self

    def __bootstrap_py_context(self) -> None:
        for imp in self.__python_context.imports:
            name = imp.get_name()
            value = self.__importer.imports(imp.module, imp.spec)
            r = reflect(var=value, name=name)
            self.add_reflection(r, reassign_name=False)

        for defined in self.__python_context.variables:
            name = defined.name
            real_value = defined.value
            if defined.model:
                model_type = self.__local_types.get(defined.model, None)
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
        if not typehint:
            return ""
        typehint = self.__local_type_names.get(typehint, None)
        if not typehint:
            typehint = get_typehint_string(typehint)
        return typehint

    def __reassign_name(self, name: str, names: Set[str]) -> str:
        if name in names:
            new_name = f"{name}.{self.__reassign_name_idx}"
            self.__reassign_name_idx += 1
            if new_name in names:
                return self.__reassign_name(name, names)
            return new_name
        return name


class BasicMOSSProvider(Provider):

    def singleton(self) -> bool:
        return False

    def contract(self) -> Type[CONTRACT]:
        return MOSS

    def factory(self, con: Container) -> Optional[CONTRACT]:
        return BasicMOSSImpl(doc="", container=con)
