import importlib
import inspect
from types import ModuleType
from typing import Optional, Any, Dict, get_type_hints, Type, List, Callable, ClassVar
import io

from ghostos.container import Container, Provider
from ghostos.contracts.modules import Modules, ImportWrapper
from ghostos.core.moss.abcd import (
    Moss,
    MossCompiler, MossRuntime, MossPrompter, MOSS_VALUE_NAME, MOSS_TYPE_NAME,
    MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
    Injection,
)
from ghostos.core.moss.pycontext import PyContext
from ghostos.prompter import Prompter, TextPrmt
from ghostos.helpers import generate_module_and_attr_name, code_syntax_check
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
        self._modules: Modules = self._container.force_fetch(Modules)
        self._predefined_locals: Dict[str, Any] = {
            # 默认代理掉 import.
            '__import__': ImportWrapper(self._modules),
        }
        self._injections: Dict[str, Any] = {}
        self._attr_prompts: List = []
        self._compiled = False
        self._closed = False

    def __del__(self):
        self.close()

    def container(self) -> Container:
        return self._container

    def pycontext(self) -> PyContext:
        return self._pycontext

    def join_context(self, context: PyContext) -> "MossCompiler":
        self._pycontext = self._pycontext.join(context)
        return self

    def with_locals(self, **kwargs) -> "MossCompiler":
        self._predefined_locals.update(kwargs)
        return self

    def with_ignore_prompts(self, *attr_names) -> "MossCompiler":
        for attr_name in attr_names:
            self._attr_prompts.append((attr_name, ""))
        return self

    def injects(self, **attrs: Any) -> "MossCompiler":
        self._injections.update(attrs)
        return self

    def _compile(self, modulename: Optional[str] = None) -> ModuleType:
        origin: Optional[ModuleType] = None
        filename = "<moss_temp_module>"
        origin_modulename = self._pycontext.module
        if origin_modulename:
            origin = importlib.import_module(origin_modulename)
            filename = origin.__file__

        if modulename is None:
            modulename = origin_modulename if origin_modulename else "__moss__"
        code = self.pycontext_code()
        # 创建临时模块.
        module = MossTempModuleType(modulename)
        MossTempModuleType.__instance_count__ += 1
        module.__dict__.update(self._predefined_locals)
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
        return MossRuntimeImpl(
            container=self._container,
            pycontext=self._pycontext.model_copy(deep=True),
            source_code=self.pycontext_code(),
            compiled=module,
            injections=self._injections,
            attr_prompts=attr_prompts,
        )

    def pycontext_code(self) -> str:
        code = self._pycontext.code
        module = self._pycontext.module
        if code is None:
            if module is None:
                return ""
            module = self._modules.import_module(self._pycontext.module)
            code = inspect.getsource(module)
        if not code.lstrip().startswith(IMPORT_FUTURE):
            code = IMPORT_FUTURE + "\n\n" + code.lstrip("\n")
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

    def __init__(self, pycontext: PyContext, container: Container, printer: Callable):
        MossStub.instance_count += 1
        self.__dict__['__pycontext__'] = pycontext
        self.__dict__['__container__'] = container
        self.__dict__['__output__'] = ""
        self.__dict__['__printer__'] = printer

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

    stub = MossStub(pycontext, container, pprint)
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
    ):
        self._container = container
        self._modules: Modules = container.force_fetch(Modules)
        self._compiled = compiled
        self._source_code = source_code
        self._pycontext = pycontext
        self._injections = injections
        self._runtime_std_output = ""
        # 初始化之后不应该为 None 的值.
        self._built: bool = False
        self._moss_prompt: Optional[str] = None
        self._attr_prompts: Dict[str, str] = attr_prompts
        self._closed: bool = False
        self._injected = set()
        self._moss: Moss = self._compile_moss()
        self._initialize_moss()
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
            # 为 None 才依赖注入.
            value = self._container.force_fetch(typehint)
            # 依赖注入.
            inject(name, value)

        self._compiled.__dict__[MOSS_VALUE_NAME] = moss
        self._compiled.__dict__[MOSS_TYPE_NAME] = moss_type
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

    def pycontext_code(
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

    def moss_injections_prompt(self) -> str:
        injections = self.moss_injections()
        children = []
        container = self.container()
        for name, injection in injections.items():
            if isinstance(injection, Prompter):
                children.append(TextPrmt(
                    title=f"moss.{name}",
                    content=injection.self_prompt(container),
                ))
        prompter = TextPrmt(
            title="Moss Injections",
        ).with_children(*children)
        return prompter.get_prompt(container)

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
