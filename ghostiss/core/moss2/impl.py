import inspect
from types import ModuleType
from typing import Optional, Any, Dict, get_type_hints, Type
import io
import json

from ghostiss.container import Container, Provider
from ghostiss.core.moss2.abc import (
    MOSS,
    MOSSCompiler, MOSSRuntime, MOSSPrompter, MOSS_NAME, MOSS_TYPE_NAME,
    MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
)
from ghostiss.core.moss2.utils import is_name_public
from ghostiss.core.moss2.libraries import Modules, ImportWrapper
from ghostiss.core.moss2.pycontext import PyContext, SerializableType, Property
from contextlib import contextmanager, redirect_stdout

IMPORT_FUTURE = "from __future__ import annotations"


class MOSSCompilerImpl(MOSSCompiler):
    def __init__(self, *, container: Container, pycontext: Optional[PyContext] = None):
        self._container = Container(parent=container)
        self._pycontext = pycontext if pycontext else PyContext()
        self._modules: Modules = self._container.force_fetch(Modules)
        self._predefined_locals: Dict[str, Any] = {
            # 默认代理掉 import.
            '__import__': ImportWrapper(self._modules),
        }
        self._injections: Dict[str, Any] = {}

    def container(self) -> Container:
        return self._container

    def pycontext(self) -> PyContext:
        return self._pycontext

    def join_context(self, context: PyContext) -> "MOSSCompiler":
        self._pycontext = self._pycontext.join(context)
        return self

    def with_locals(self, **kwargs) -> "MOSSCompiler":
        self._predefined_locals.update(kwargs)
        return self

    def injects(self, **attrs: Any) -> "MOSSCompiler":
        self._injections.update(attrs)
        return self

    def _compile(self, modulename: str) -> ModuleType:
        code = self.pycontext_code(model_visible_only=False)
        module = ModuleType(modulename)
        module.__dict__.update(self._predefined_locals)
        compiled = compile(code, modulename, "exec")
        exec(compiled, module.__dict__)
        return module

    def _new_runtime(self, module: ModuleType) -> "MOSSRuntime":
        return MossRuntimeImpl(
            container=self._container,
            pycontext=self._pycontext,
            source_code=self.pycontext_code(model_visible_only=False),
            compiled=module,
            injections=self._injections,
        )

    def pycontext_code(self, model_visible_only: bool = True) -> str:
        code = self._pycontext.code
        if code is None and self._pycontext.module:
            module = self._modules.import_module(self._pycontext.module)
            code = inspect.getsource(module)
        if not code.lstrip().startswith(IMPORT_FUTURE):
            code = IMPORT_FUTURE + "\n\n" + code.lstrip("\n")
            return code
        return code if code else ""

    def destroy(self) -> None:
        # container 先不 destroy.
        del self._container
        del self._pycontext
        del self._predefined_locals
        del self._injections


class MossStub(MOSS):

    def __init__(self, compiled: ModuleType, pycontext: PyContext):
        # 由于定义了 __set_attr__, 所以直接用 __dict__ 赋值.
        self.__dict__["_pycontext"] = pycontext
        self.__dict__["_compiled"] = compiled
        self.__module__ = compiled.__name__

    def __bootstrap_pycontext__(self):
        # 初始化 pycontext variable
        for name, var in self._pycontext.properties.items():
            value = var.generate_value(self._compiled)
            self.__dict__[name] = value

    # def var(self, name: str, value: SerializableType, desc: Optional[str] = None, force: bool = False) -> bool:
    #     if not isinstance(value, SerializableType):
    #         raise AttributeError(f"'{type(value)}' is not Serializable")
    #     if not force and name in self._pycontext.properties:
    #         return False
    #     p = Property.from_value(name, value, desc)
    #     self._pycontext.properties[name] = p

    def __setattr__(self, name: str, value):
        """
        支持直接用 Property 来赋值.
        """
        if not name.startswith("_"):
            if isinstance(value, Property):
                value = value.generate_value(self._compiled)
                self._pycontext.properties[name] = value
            elif name in self._pycontext.properties:
                prop = self._pycontext.properties[name]
                # 同步保存到 pycontext.
                prop.set_value(value)
        self.__dict__[name] = value

    def __getattr__(self, name: str):
        value = self.__dict__.get(name, None)
        if value is not None and isinstance(value, Property):
            value = value.generate_value(self._compiled)
        return value

    def __pycontext__(self) -> PyContext:
        return self._pycontext

    def __destroy__(self):
        del self._pycontext
        del self._compiled


class MossRuntimeImpl(MOSSRuntime, MOSSPrompter):

    def __init__(
            self, *,
            container: Container,
            pycontext: PyContext,
            source_code: str,
            compiled: ModuleType,
            injections: Dict[str, Any],
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
        self._moss: Optional[MossStub] = None
        self._moss_prompt: Optional[str] = None
        self._bootstrap_moss()

    def _bootstrap_moss(self):
        if self._built:
            return
        self._built = True
        self._compile_moss()

    def _compile_moss(self):
        moss_type = self.moss_type()

        # 创建 stub.
        pycontext = self._pycontext.model_copy(deep=True)
        moss = MossStub(self._compiled, pycontext)
        members = inspect.getmembers(moss_type, lambda a: inspect.isclass(a) or inspect.ismethod(a))
        # 复制 moss type 原有的类或者属性定义.
        for name, member in members:
            # moss 类不允许传递私有变量.
            if is_name_public(name) and name not in pycontext.properties:
                setattr(moss, name, member)

        # 初始化 injection. 强制赋值.
        for name, injection in self._injections.items():
            # 可以定义私有变量.
            if name not in pycontext.properties:
                setattr(moss, name, injection)
        # 初始化 pycontext injection. 强制赋值.
        for name, injection in self._pycontext.injections.items():
            injection_module, injection_spec = injection.get_from_module_attr()
            value = self._modules.import_module(injection_module)
            if injection_spec:
                value = value.__dict__.get(injection_spec, None)
            if value is None:
                raise ModuleNotFoundError(f"inject from {injection_module}, {injection_spec} failed, not found")
            setattr(moss, name, value)

        # 初始化基于容器的依赖注入.
        typehints = get_type_hints(moss_type)
        for name, typehint in typehints.items():
            if name.startswith('_'):
                continue

            # 已经有的就不再注入.
            if hasattr(moss, name):
                continue
            value = getattr(moss_type, name, None)
            if value is None:
                value = self._container.get(typehint)
            # 依赖注入.
            setattr(moss, name, value)
        # pycontext 的优先级最高了.
        moss.__bootstrap_pycontext__()

        self._moss = moss
        self._compiled.__dict__[MOSS_NAME] = moss
        self._compiled.__dict__[MOSS_TYPE_NAME] = moss_type

    def container(self) -> Container:
        return self._container

    def prompter(self) -> MOSSPrompter:
        return self

    def module(self) -> ModuleType:
        return self._compiled

    def locals(self) -> Dict[str, Any]:
        return self._compiled.__dict__

    def moss(self) -> object:
        return self._moss

    def dump_context(self) -> PyContext:
        return self._moss.__pycontext__()

    def dump_std_output(self) -> str:
        return self._runtime_std_output

    @contextmanager
    def runtime_ctx(self):
        # 保存原始的stdout
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            yield
        self._runtime_std_output += str(buffer.getvalue())

    def pycontext_code(
            self,
            model_visible: bool = True,
    ) -> str:
        code = self._source_code
        return self._parse_pycontext_code(code, model_visible)

    @staticmethod
    def _parse_pycontext_code(code: str, model_visible: bool = True) -> str:
        lines = code.split("\n")
        results = []
        hide = False
        for line in lines:
            if line.startswith(MOSS_HIDDEN_MARK):
                hide = True
            if hide and model_visible:
                continue
            if not hide or not model_visible:
                results.append(line)
            elif line.startswith(MOSS_HIDDEN_UNMARK):
                hide = False
        return "\n".join(results)

    def destroy(self) -> None:
        self._container.destroy()
        self._moss.__destroy__()
        del self._container
        del self._injections
        del self._compiled
        del self._moss


class TestMOSSProvider(Provider[MOSSCompiler]):
    """
    用于测试的标准 compiler.
    但实际上好像也是这个样子.
    """

    def singleton(self) -> bool:
        return False

    def contract(self) -> Type[MOSSCompiler]:
        return MOSSCompiler

    def factory(self, con: Container) -> MOSSCompiler:
        return MOSSCompilerImpl(container=con, pycontext=PyContext())
