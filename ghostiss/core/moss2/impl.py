import inspect
from types import ModuleType
from typing import Optional, Any, Dict, Set, Union, get_type_hints
import sys
import io
import json

from ghostiss.container import Container
from ghostiss.core.moss2.abc import (
    MOSS,
    MOSSCompiler, MOSSRuntime, MOSSPrompter, MOSSResult, MOSS_NAME, MOSS_TYPE_NAME,
    MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
)
from ghostiss.core.moss2.libraries import Modules
from ghostiss.core.moss2.pycontext import PyContext, SerializableType, Property
from contextlib import contextmanager, redirect_stdout, redirect_stderr

IMPORT_FUTURE = "from __future__ import annotations"


class MOSSCompilerImpl(MOSSCompiler):
    def __init__(self, *, container: Container, pycontext: Optional[PyContext] = None):
        self._container = Container(parent=container)
        self._pycontext = pycontext if pycontext else PyContext()
        self._modules: Modules = self._container.force_fetch(Modules)
        self._predefined_locals: Dict[str, Any] = {}
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
            source_code = inspect.getsource(module)
            if not source_code.lstrip().startswith(IMPORT_FUTURE):
                source_code = IMPORT_FUTURE + "\n" + source_code
                return source_code
        return code if code else ""

    def destroy(self) -> None:
        # container 先不 destroy.
        del self._container
        del self._pycontext
        del self._predefined_locals
        del self._injections


class MossStub(MOSS):

    def __init__(self, module: ModuleType, pycontext: PyContext):
        self._pycontext = pycontext
        self.__module__ = module.__name__
        # 初始化 pycontext variable
        for name, var in self._pycontext.properties.items():
            value = var.generate_value()
            setattr(self, name, value)

    # def var(self, name: str, value: SerializableType, desc: Optional[str] = None, force: bool = False) -> bool:
    #     if not isinstance(value, SerializableType):
    #         raise AttributeError(f"'{type(value)}' is not Serializable")
    #     if not force and name in self._pycontext.properties:
    #         return False
    #     p = Property.from_value(name, value, desc)
    #     self._pycontext.properties[name] = p

    def __resolve__(self) -> PyContext:
        properties = {}
        # 将上下文中可继承的数据都进行传递.
        for name, prop in self.__dict__:
            if isinstance(prop, SerializableType):
                try:
                    _ = json.dumps(prop)
                    properties[name] = Property.from_value(
                        name=name,
                        value=prop
                    )
                except TypeError:
                    continue
        self._pycontext.properties = properties
        return self._pycontext

    def __destroy__(self):
        del self._pycontext


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
        moss = MossStub(self._compiled, self._pycontext.model_copy(deep=True))
        members = inspect.getmembers(moss_type, lambda a: inspect.isclass(a) or inspect.ismethod(a))
        # 复制 moss type 原有的类或者属性定义.
        for name, member in members:
            setattr(moss, name, member)

        # 初始化 injection. 强制赋值.
        for name, injection in self._injections.items():
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
        return self._moss.__resolve__()

    def dump_std_output(self) -> str:
        return self._runtime_std_output

    @contextmanager
    def runtime_ctx(self):
        # 保存原始的stdout
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            yield
        self._runtime_std_output += "\n" + str(buffer.getvalue())

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
            if line == MOSS_HIDDEN_MARK:
                hide = True
            if hide and model_visible:
                continue
            if not hide or not model_visible:
                results.append(line)
            elif line == MOSS_HIDDEN_UNMARK:
                hide = False
        return "\n".join(results)

    def moss_type_prompt(self) -> str:
        moss_type = self.moss_type()

    def destroy(self) -> None:
        self._container.destroy()
        self._moss.__destroy__()
        del self._container
        del self._injections
        del self._compiled
        del self._moss
