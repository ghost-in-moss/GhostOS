from types import ModuleType
from typing import Optional, Any, Dict, Set, Union

from ghostiss.container import Container
from ghostiss.moss2.abc import MOSS, MOSSRuntime, MOSSCompiler
from ghostiss.moss2.prompts import Prompter
from ghostiss.moss2.pycontext import SerializableType, Variable, PyContext
from contextlib import contextmanager


class MOSSCompilerImpl(MOSSCompiler):

    def __init__(self, doc: str, container: Container, pycontext: Optional[Container] = None) -> None:
        self._doc: str = doc
        self._container = Container(parent=container)
        self._container.set(MOSSCompiler, self)
        if pycontext is None:
            pycontext = PyContext()
        self._pycontext = pycontext

    def container(self) -> Container:
        return self._container

    def pycontext(self) -> PyContext:
        return self._pycontext

    def join_context(self, context: PyContext) -> "MOSSCompiler":
        self._pycontext = self._pycontext.join(context)
        return self

    def _compile(self, meta_mode: bool = False) -> "MOSSRuntime":
        pass

    def destroy(self) -> None:
        self._container.destroy()
        del self._container
        del self._pycontext


class MOSSImpl(MOSS):
    def __init__(self, runtime: MOSSRuntime):
        self._runtime = runtime
        self._injected: Dict[str, Variable] = {}
        self._reserved_names: Set = set()
        self._injected_type_to_names: Dict[type, str] = {}
        self._injected_prompter: Dict[str, Prompter] = {}

    def define(self, name: str, value: SerializableType, desc: Optional[str] = None, force: bool = False) -> bool:
        pycontext = self._runtime.pycontext()
        if name in pycontext.variables and not force:
            return False
        var = Variable.from_value(name, value, desc)
        pycontext.define(var)
        self._add_attr(name, value)
        return True

    def _add_attr(self, name: str, value: Any) -> None:
        pass

    def inject(self, modulename: str, **specs: str) -> None:
        pass

    def remove(self, name: str) -> None:
        pass

    def __del__(self):
        self.__dict__ = {}
        del self._runtime
        del self._injected
        del self._reserved_names


class MOSSRuntimeImpl(MOSSRuntime):

    def __init__(self, container: Container, pycontext: PyContext, modulename: str):
        self._container = container
        self._pycontext = pycontext
        self._moss = MOSSImpl(runtime=self)
        self._compiled: ModuleType = ModuleType(modulename)

        # 初始化绑定.
        self._container.set(MOSS, self._moss)

    def container(self) -> Container:
        return self._container

    def injects(self, **attrs: Union[Any, Prompter]) -> "MOSSCompiler":
        pass

    def predefined_code(self, model_visible: bool = True) -> str:
        pass

    def predefined_code_prompt(self) -> str:
        pass

    def moss(self) -> MOSS:
        pass

    def moss_prompt(self) -> str:
        pass

    def compiled(self) -> ModuleType:
        pass

    def locals(self) -> Dict[str, Any]:
        pass

    def pycontext(self) -> PyContext:
        pass

    def dump_context(self) -> PyContext:
        return self._pycontext.model_copy(deep=True)

    def dump_std_output(self) -> str:
        pass

    def exec_ctx(self):
        pass
