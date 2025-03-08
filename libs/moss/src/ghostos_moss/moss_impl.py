import importlib
import inspect
from types import ModuleType, FunctionType
from typing import Optional, Any, Dict, get_type_hints, Type, List, Callable, ClassVar, Union
import io
from typing_extensions import Self

from ghostos_container import Container, Provider
from ghostos_moss.abcd import (
    Moss,
    MossCompiler, MossRuntime, MossPrompter, MOSS_VALUE_NAME, MOSS_TYPE_NAME,
    MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
    Injection,
)
from ghostos_moss.modules import Modules, ImportWrapper, DefaultModules
from ghostos_moss.prompts import reflect_code_prompt
from ghostos_moss.pycontext import PyContext
from ghostos_moss.exports import Exporter
from ghostos_moss.magics import replace_magic_prompter
from ghostos_moss.self_updater import SelfUpdaterProvider
from ghostos_common.helpers import (
    generate_module_and_attr_name, code_syntax_check, get_code_interface_str,
    import_from_path,
)
from ghostos_moss.utils import is_typing, is_subclass
from contextlib import contextmanager, redirect_stdout

IMPORT_FUTURE = "from __future__ import annotations"

__all__ = [
    'MossStub',
    'MossCompilerImpl',
    'MossRuntimeImpl',
    'DefaultMOSSProvider',
    'MossTempModuleType',
]


class MossTempModuleType(ModuleType):
    __instance_count__: ClassVar[int] = 0

    def __del__(self):
        if MOSS_VALUE_NAME in self.__dict__:
            del self.__dict__[MOSS_VALUE_NAME]
        MossTempModuleType.__instance_count__ -= 1


class MossCompilerImpl(MossCompiler):
    def __init__(self, *, container: Container, pycontext: Optional[PyContext] = None):
        self._container = Container(parent=container, name="moss")
        self._pycontext = pycontext if pycontext else PyContext()
        modules = container.get(Modules)
        if modules is None:
            modules = DefaultModules()
            self._container.set(Modules, modules)
        self._modules: Modules = modules
        self._default_moss_type = Moss

        # prepare values.
        self._predefined_locals: Dict[str, Any] = {
            # 默认代理掉 import.
            '__import__': ImportWrapper(self._modules),
        }
        self._injections: Dict[str, Any] = {}
        self._attr_prompts: List = []
        # the default ignored modules
        self._ignored_modules = [
            'pydantic',
            'typing',
            'typing_extensions',
            'inspect',
            'abc',
            'openai',
        ]
        self._compiled = False
        self._closed = False

    def __del__(self):
        self.close()

    def container(self) -> Container:
        return self._container

    def with_default_moss_type(self, moss_type: Union[Type[Moss], str]) -> Self:
        if isinstance(moss_type, str):
            moss_type = import_from_path(moss_type, self._modules.import_module)
        if not isinstance(moss_type, type) or not issubclass(moss_type, Moss):
            raise TypeError(f"default moss type {moss_type} is not a subclass of Moss")
        self._default_moss_type = moss_type
        return self

    def pycontext(self) -> PyContext:
        return self._pycontext

    def join_context(self, context: PyContext) -> "MossCompiler":
        self._pycontext = self._pycontext.join(context)
        return self

    def with_locals(self, **kwargs) -> "MossCompiler":
        self._predefined_locals.update(kwargs)
        return self

    def with_ignored_imported(self, module_names: List[str]) -> "MossCompiler":
        self._ignored_modules = module_names
        return self

    def injects(self, **attrs: Any) -> "MossCompiler":
        self._injections.update(attrs)
        return self

    def _compile(self, modulename: Optional[str] = None) -> ModuleType:
        origin: Optional[ModuleType] = None
        filename = "<moss_temp_module>"
        origin_modulename = self._pycontext.module
        # 没有任何设定的情况下.
        if origin_modulename is None and self._pycontext.code is None:
            # 认为传入的 modulename 就是要编译的 module
            self._pycontext.module = modulename
            origin_modulename = modulename

        self._container.bootstrap()
        if origin_modulename:
            origin = importlib.import_module(origin_modulename)
            filename = origin.__file__

        # 编译的 module name.
        if modulename is None:
            modulename = origin_modulename if origin_modulename else "__moss__"

        code = self.pycontext_code()
        # 创建临时模块.
        module = MossTempModuleType(modulename)
        MossTempModuleType.__instance_count__ += 1
        module.__dict__.update(self._predefined_locals)
        if MOSS_TYPE_NAME not in module.__dict__:
            module.__dict__[MOSS_TYPE_NAME] = self._default_moss_type
        module.__dict__["__origin_moss__"] = Moss
        module.__file__ = filename
        compiled = compile(code, modulename, "exec")
        exec(compiled, module.__dict__)
        if origin is not None:
            updating = self._filter_origin(origin)
            module.__dict__.update(updating)
        return module

    @staticmethod
    def _filter_origin(origin: ModuleType) -> Dict[str, Any]:
        result = {}
        for attr_name, attr_value in origin.__dict__.items():
            if attr_name.startswith("__"):
                continue
            if inspect.isclass(attr_value) or inspect.isfunction(attr_value):
                if attr_value.__module__ != origin.__name__:
                    continue
                result[attr_name] = attr_value
        return result

    def _new_runtime(self, module: ModuleType) -> "MossRuntime":
        attr_prompts = {}
        for attr_name, value in self._attr_prompts:
            attr_prompts[attr_name] = value
        self._compiled = True

        # default moss container bindings
        self._container.register(SelfUpdaterProvider())

        return MossRuntimeImpl(
            container=self._container,
            pycontext=self._pycontext.model_copy(deep=True),
            source_code=self.pycontext_code(),
            compiled=module,
            injections=self._injections,
            attr_prompts=attr_prompts,
            ignored_modules=self._ignored_modules,
        )

    def pycontext_code(self) -> str:
        code = self._pycontext.code
        module = self._pycontext.module
        if code is None:
            if module is None:
                return ""
            module = self._modules.import_module(self._pycontext.module)
            code = inspect.getsource(module)
        return code if code else ""

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        # container 先不 destroy.
        if not self._compiled:
            self._container.shutdown()
        del self._container
        del self._pycontext
        del self._predefined_locals
        del self._injections


class MossStub(Moss):
    instance_count: ClassVar[int] = 0
    __pycontext__: PyContext
    __container__: Container
    __output__: str
    __printer__: Callable

    def __init__(
            self,
            pycontext: PyContext,
            container: Container,
            printer: Callable,
            watching: List,
            ignored: List,
    ):
        MossStub.instance_count += 1
        self.__dict__['__pycontext__'] = pycontext
        self.__dict__['__container__'] = container
        self.__dict__['__output__'] = ""
        self.__dict__['__printer__'] = printer
        self.__dict__['__watching__'] = watching
        self.__dict__['__ignored__'] = ignored

    def fetch(self, abstract: Moss.T) -> Optional[Moss.T]:
        return self.__container__.fetch(abstract)

    def pprint(self, *args, **kwargs) -> None:
        return self.__printer__(*args, **kwargs)

    def __setattr__(self, _name, _value):
        if self.__pycontext__.allow_prop(_value):
            self.__pycontext__.set_prop(_name, _value)
        self.__dict__[_name] = _value

    def __del__(self):
        MossStub.instance_count -= 1


def new_moss_stub(cls: Type[Moss], container: Container, pycontext: PyContext, pprint: Callable) -> Moss:
    # cls 必须不包含参数.

    watching = cls.__watching__
    stub = MossStub(pycontext, container, pprint, watching, cls.__ignored__)
    stub.executing_code = None
    # assert stub.instance_count > 0
    for attr_name in dir(cls):
        if not attr_name.startswith("_") and not hasattr(stub, attr_name):
            attr_value = getattr(cls, attr_name)
            setattr(stub, attr_name, attr_value)

    # 反向注入.
    for name, value in cls.__dict__.items():
        if name in pycontext.properties or name.startswith("_"):
            continue
        if stub.__pycontext__.allow_prop(value):
            stub.__pycontext__.set_prop(name, value)

    return stub


class MossRuntimeImpl(MossRuntime, MossPrompter):

    def __init__(
            self, *,
            container: Container,
            pycontext: PyContext,
            source_code: str,
            compiled: ModuleType,
            injections: Dict[str, Any],
            attr_prompts: Dict[str, str],
            ignored_modules: List[str],
    ):
        self._container = container
        self._modules: Modules = container.force_fetch(Modules)
        self._compiled = compiled
        self._source_code = source_code
        self._pycontext = pycontext
        self._container.set(PyContext, self._pycontext)
        self._injections = injections
        self._runtime_std_output = ""
        # 初始化之后不应该为 None 的值.
        self._built: bool = False
        self._moss_prompt: Optional[str] = None
        self._attr_prompts: Dict[str, str] = attr_prompts
        self._imported_attrs: Optional[Dict[str, Any]] = None
        self._closed: bool = False
        self._injected = set()
        self._injected_types: Dict[Any, str] = {}
        self._moss: Moss = self._compile_moss()
        self._initialize_moss()
        self._ignored_modules = set(ignored_modules) | set(self._moss.__ignored__)

        self._replaced_magic_prompts = replace_magic_prompter(self._compiled)
        MossRuntime.instance_count += 1

    def _compile_moss(self) -> Moss:
        moss_type = self.moss_type()
        if not issubclass(moss_type, Moss):
            raise TypeError(f"Moss type {moss_type} is not subclass of {generate_module_and_attr_name(Moss)}")

        # 创建 stub.
        pycontext = self._pycontext
        moss = new_moss_stub(moss_type, self._container, pycontext, self.pprint)
        return moss

    def _initialize_moss(self) -> None:
        from .lifecycle import __moss_compiled__
        moss = self._moss
        pycontext = self._pycontext
        moss_type = self.moss_type()

        def inject(attr_name: str, injected: Any) -> Any:
            if isinstance(injected, Injection):
                injected.on_inject(self, attr_name)
            setattr(moss, attr_name, injected)
            self._injected.add(attr_name)

        # 初始化 pycontext variable
        for name, prop in pycontext.iter_props(self._compiled):
            # 直接用 property 作为值.
            inject(name, prop)

        # 反向注入

        for name, injection in self._injections.items():
            inject(name, injection)

        # 初始化基于容器的依赖注入.
        typehints = get_type_hints(moss_type, localns=self._compiled.__dict__)
        for name, typehint in typehints.items():
            if name.startswith('_'):
                continue

            # 已经有的就不再注入.
            if hasattr(moss, name):
                continue

            # 记录所有定义过的类型.
            self._injected_types[typehint] = name
            # 为 None 才依赖注入.
            value = self._container.force_fetch(typehint)
            # 依赖注入.
            inject(name, value)

        self._compiled.__dict__[MOSS_VALUE_NAME] = moss
        fn = __moss_compiled__
        if __moss_compiled__.__name__ in self._compiled.__dict__:
            fn = self._compiled.__dict__[__moss_compiled__.__name__]
        fn(moss)
        self._moss = moss

    def container(self) -> Container:
        return self._container

    def prompter(self) -> MossPrompter:
        return self

    def lint_exec_code(self, code: str) -> Optional[str]:
        source_code = self._source_code
        new_code = source_code + "\n\n" + code.strip()
        return code_syntax_check(new_code)

    def module(self) -> ModuleType:
        return self._compiled

    def locals(self) -> Dict[str, Any]:
        return self._compiled.__dict__

    def moss(self) -> Moss:
        return self._moss

    def dump_pycontext(self) -> PyContext:
        return self._pycontext

    def dump_std_output(self) -> str:
        return self._runtime_std_output

    def pprint(self, *args: Any, **kwargs: Any) -> None:
        from pprint import pprint
        out = io.StringIO()
        with redirect_stdout(out):
            pprint(*args, **kwargs)
        self._runtime_std_output += str(out.getvalue())

    @contextmanager
    def redirect_stdout(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            yield
            self._runtime_std_output += str(buffer.getvalue())

    def get_source_code(
            self,
            exclude_hide_code: bool = True,
    ) -> str:
        code = self._source_code
        return self._parse_pycontext_code(code, exclude_hide_code)

    def moss_injections(self) -> Dict[str, Any]:
        moss = self.moss()
        injections = {}
        for name in self._injected:
            injection = getattr(moss, name)
            injections[name] = injection
        return injections

    def replaced_magic_prompts(self) -> Dict[str, str]:
        return self._replaced_magic_prompts

    def get_imported_attrs(self) -> Dict[str, Any]:
        if self._imported_attrs is None:
            self._imported_attrs = {}
            self_modulename = self._compiled.__module__
            for name, value in self._compiled.__dict__.items():
                if name.startswith("_"):
                    continue
                elif not value:
                    continue
                elif inspect.isbuiltin(value):
                    # 系统内置的, 都不展示.
                    continue
                elif inspect.ismodule(value):
                    # module can not get itself
                    self._imported_attrs[name] = value
                elif hasattr(value, "__module__"):
                    value_module = value.__module__
                    if value_module == self_modulename:
                        continue
                    self._imported_attrs[name] = value
        return self._imported_attrs

    def _is_ignored(self, modulename: str) -> bool:
        if modulename in self._ignored_modules:
            return True
        for ignored in self._ignored_modules:
            ignored_prefix = ignored.rstrip('.') + '.'
            if modulename.startswith(ignored_prefix):
                return True
        return False

    def get_imported_attrs_prompt(self, includes: List = None) -> str:
        # todo: make build class later
        imported_attrs = self.get_imported_attrs()
        reverse_imported: Dict[Any, str] = {Moss: "__origin_moss__"}
        # the types need to reflect.
        reflection_types = {Moss}

        # add all function and method to reflections.
        # and prepare reverse imported.
        for key, value in imported_attrs.items():
            if value not in reverse_imported:
                reverse_imported[value] = key
                # only function or methods are reflected automatically
                if isinstance(value, type):
                    if inspect.isabstract(value) or is_subclass(value, Exporter):
                        reflection_types.add(value)
                elif inspect.isroutine(value):
                    reflection_types.add(value)
                elif is_typing(value):
                    reflection_types.add(value)
        if includes:
            for value in includes:
                if value not in reverse_imported:
                    continue
                reflection_types.add(value)

        # add injected first .
        for injected_type in self._injected_types:
            # only imported value shall be reflected.
            reflection_types.add(injected_type)
            if injected_type not in reverse_imported:
                property_name = self._injected_types[injected_type]
                reverse_imported[injected_type] = f"{Moss}.{property_name}"

        for watched in self.moss().__watching__:
            if watched in reverse_imported:
                reflection_types.add(watched)

        blocks = []
        functions = []
        classes = []
        modules = []
        module_names = set()
        others = []
        for reflection_type in reflection_types:
            if inspect.isclass(reflection_type):
                classes.append(reflection_type)
            elif inspect.ismodule(reflection_type):
                modules.append(reflection_type)
                module_names.add(reflection_type.__name__)
            elif inspect.isroutine(reflection_type):
                functions.append(reflection_type)
            else:
                others.append(reflection_type)
        if len(functions) > 0:
            blocks.append("#<routines>")
            for item in functions:
                name = reverse_imported[item]
                item_module = item.__module__
                if self._is_ignored(item_module) or item_module in module_names:
                    continue
                prompt = reflect_code_prompt(item)
                if not prompt:
                    continue
                name_desc = f" name=`{name}`" if name != item.__name__ else ""
                if name_desc:
                    block = f"#<attr{name_desc} module=`{item_module}`>\n{prompt}\n#</attr>"
                else:
                    block = prompt
                blocks.append(block)
            blocks.append("#</routines>")
        if len(classes) > 0:
            blocks.append("#<classes>")
            for item in classes:
                name = reverse_imported[item]
                item_module = item.__module__
                if self._is_ignored(item_module) or item_module in module_names:
                    continue
                name_desc = f" name=`{name}`" if name != item.__name__ else ""
                prompt = reflect_code_prompt(item)
                if not prompt:
                    continue
                if name_desc:
                    block = f"#<attr{name_desc} module=`{item_module}`>\n{prompt}\n#</attr>"
                else:
                    block = prompt
                blocks.append(block)
            blocks.append("#</classes>")
        if len(modules) > 0:
            blocks.append("#<modules>")
            for item in modules:
                name = reverse_imported[item]
                item_module = item.__name__
                if self._is_ignored(item_module):
                    continue
                source = inspect.getsource(item)
                if not source:
                    continue
                prompt = get_code_interface_str(source)
                if prompt:
                    block = f"#<attr name=`{name}` module=`{item_module}`>\n{prompt}\n#</attr>"
                    blocks.append(block)
            blocks.append("#</modules>")
        if len(others) > 0:
            blocks.append("#<others>")
            for item in others:
                name = reverse_imported[item]
                prompt = reflect_code_prompt(item)
                if prompt:
                    type_ = type(item).__name__
                    block = f"#<attr name=`{name}` type=`{type_}`>\n{prompt}\n# </attr>"
                    blocks.append(block)
            blocks.append("#</others>")

        return "\n\n".join(blocks)

    @staticmethod
    def _parse_pycontext_code(code: str, exclude_hide_code: bool = True) -> str:
        if not exclude_hide_code:
            return code

        lines = code.split("\n")
        results = []
        num_hidden_mark = 0
        hide = False
        for line in lines:
            if line.lstrip().startswith(MOSS_HIDDEN_MARK):
                num_hidden_mark += 1
                hide = True
            elif line.lstrip().startswith(MOSS_HIDDEN_UNMARK):
                num_hidden_mark -= 1
                if num_hidden_mark <= 0:
                    hide = False
            else:
                if hide:
                    continue
                else:
                    results.append(line)

        return "\n".join(results)

    def update_executing_code(self, code: Optional[str] = None) -> None:
        if code is None:
            return
        self._pycontext.execute_code = code
        self._moss.executing_code = code

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        data = self._moss.__dict__
        for val in data.values():
            if isinstance(val, Injection):
                val.on_destroy()
        self._container.shutdown()

    def __del__(self):
        if not self._closed:
            self.close()
        MossRuntime.instance_count -= 1
        del self._container
        del self._injections
        del self._compiled
        del self._moss
        del self._pycontext


class DefaultMOSSProvider(Provider[MossCompiler]):
    """
    用于测试的标准 compiler.
    但实际上好像也是这个样子.
    """

    def singleton(self) -> bool:
        return False

    def contract(self) -> Type[MossCompiler]:
        return MossCompiler

    def factory(self, con: Container) -> MossCompiler:
        return MossCompilerImpl(container=con, pycontext=None)
