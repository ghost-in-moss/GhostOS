from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Dict, Union, Optional, Any, Type
from pydantic import BaseModel, Field
from ghostiss.interfaces8.promptable import PromptAble
from ghostiss.interfaces8.messages import Attachment

if TYPE_CHECKING:
    from ghostiss.interfaces8.operators import Operator


class Import(BaseModel):
    """
    import 各种库.
    """
    module: str
    values: List[str]
    aliases: Dict[str]


VARIABLE_TYPES = Union[str, int, float, bool, None, List, Dict]


class Definition(BaseModel):
    """
    需要在上下文中还原的代码.
    """
    name: str
    source_code: str


class Variable(BaseModel):
    """
    可以被序列化的变量.
    """
    name: str
    desc: str
    value: VARIABLE_TYPES = Field(default=None, description="")
    clazz: str = Field(description="如果是 pydantic 等类型, 可以通过类进行封装. 类应该在 imports 或者 defines 里.")


# --- futures --- #

class Future(BaseModel):
    call_id: str
    variable: Variable


class FutureCall(BaseModel):
    call_id: str
    name: str
    arguments: Dict


class FutureCalls(Attachment):
    attachment_name = "future_calls"
    calls: List[FutureCall]


class FutureCallback(BaseModel):
    call_id: str
    callback: Dict


class FutureCallbacks(Attachment):
    attachment_name = "reaction_callbacks"
    callbacks: List[FutureCallback]


# --- python context that transportable --- #

class PyContext(BaseModel):
    """
    可传输的 python 上下文.
    不需要全部用 pickle 之类的库做序列化, 方便管理 bot 的思维空间.
    """

    imports: List[Import] = Field(default_factory=list, description="通过 python 引入的包, 类, 方法 等.")
    defines: List[Definition] = Field(default_factory=list, description="上下文中预定义的方法或类, 可以修改")
    variables: List[Variable] = Field(default_factory=list, description="在上下文中定义的变量.")
    futures: List[Future] = Field(default_factory=list)

    def left_join(self, ctx: "PyContext") -> "PyContext":
        raise NotImplemented("todo")

    def right_join(self, ctx: "PyContext") -> "PyContext":
        pass

    def callback(self, callback: FutureCallback) -> None:
        futures = []
        for future in self.futures:
            if future.id == callback.id:
                future.var.value = callback.value
                self.variables.append(future.var)
            else:
                futures.append(future)
        self.futures = futures


class PyLibrary(PromptAble, ABC):
    """
    可以在 python 环境里运行的类.
    """

    @abstractmethod
    def as_local_vars(self) -> Dict[str, Any]:
        pass


class Observation(BaseModel):
    prompt: str
    prints: List[str]
    error: str = Field(default="")


class Breakpoint(ABC):

    @abstractmethod
    def context(self) -> PyContext:
        pass

    @abstractmethod
    def observation(self) -> Observation:
        pass

    @abstractmethod
    def operator(self) -> Operator["Operator"]:
        pass


class PyRuntime(ABC):

    @abstractmethod
    def context(self) -> PyContext:
        pass

    @abstractmethod
    def local_types(self) -> Dict[str, Type]:
        pass

    @abstractmethod
    def local_vars(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def run(self, code: str, function_call: Optional[str] = None) -> "Breakpoint":
        pass


class Interpreter(ABC):

    @abstractmethod
    def prompt(self, ctx: PyContext) -> str:
        pass

    @abstractmethod
    def runtime(
            self,
            ctx: PyContext,
            runnable: List[PyLibrary],
    ) -> PyRuntime:
        pass


class Python(ABC):
    pass
