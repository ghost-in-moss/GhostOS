from typing import Dict, Any, Union, List, Optional, Tuple
from pydantic import BaseModel, Field
import inspect
from ghostiss.helpers import parse_import_module_and_spec
from ghostiss.container import Container


# --- python context that transportable --- #

class PyContext(BaseModel):
    """
    可传输的 python 上下文.
    不需要全部用 pickle 之类的库做序列化, 方便管理 bot 的思维空间.
    """

    module: Optional[str] = Field(
        default=None,
        description="the module path that from which import the moss context predefined code",
    )
    injections: Dict[str, "Injected"] = Field(
        default_factory=dict,
        description="通过 python 引入的包, 类, 方法 等.",
    )
    variables: Dict[str, "Variable"] = Field(
        default_factory=dict,
        description="在上下文中定义的变量.",
    )

    def inject(self, imp: "Injected") -> None:
        self.injections[imp.get_import_path()] = imp

    def define(self, d: "Variable") -> None:
        self.variables[d.name] = d

    def join(self, ctx: "PyContext") -> "PyContext":
        """
        合并两个 python context, 以右侧的为准. 并返回一个新的 PyContext 对象. 避免左向污染.
        """
        copied = self.model_copy(deep=True)
        if ctx.module:
            copied.module = ctx.module
        for imp in ctx.injections.values():
            copied.inject(imp)
        for var in ctx.variables.values():
            copied.define(var)
        return copied


class Injected(BaseModel):
    """
    from module import specific attribute then inject to MOSS Context
    """
    module: str = Field(
        description="the imported module name or use module path pattern such as 'modulename:attr_name'",
    )
    spec: Optional[str] = Field(
        default=None,
        description="the specific attribute name from the module. could be None if defined in self.module",
    )
    alias: Optional[str] = Field(default=None, description="context attr alias for the imported value")

    @classmethod
    def reflect(cls, value: Any, alias: Optional[str] = None) -> "Injected":
        """
        reflect a value and generate Imported value.
        :param value:
        :param alias:
        :return:
        """
        modulename = inspect.getmodulename(value)
        if inspect.ismodule(value):
            spec = None
        else:
            spec = getattr(value, '__name__', None)
        return Injected(
            module=modulename,
            spec=spec,
            alias=alias,
        )

    def get_name(self) -> str:
        if self.alias:
            return self.alias
        _, spec = self.get_from_module_attr()
        return spec

    def get_from_module_attr(self) -> Tuple[str, Optional[str]]:
        """
        :return: modulename and attribute name from the module
        """
        if self.spec:
            return self.module, self.spec
        return parse_import_module_and_spec(self.module)

    def get_import_path(self) -> str:
        module, spec = self.get_from_module_attr()
        spec = ":" + spec if spec else ""
        return module + spec


SerializableType = Union[str, int, float, bool, None, List, Dict, BaseModel]
"""系统支持的各种可序列化类型, 可以被存储到 Serializable 里. 更多情况下可以用别的变量类型. """


class Variable(BaseModel):
    """
    可以在上下文中声明的变量.
    """
    name: str = Field()
    desc: Optional[str] = Field(default=None)
    value: SerializableType = Field(default=None, description="")
    model: Optional[str] = Field(
        default=None,
        description="如果是 pydantic 等类型, 可以通过类进行封装. 类应该在 imports 或者 defines 里.",
    )

    @classmethod
    def from_value(cls, name: str, value: Any, desc: str) -> Optional["Variable"]:
        pass

    def generate_value(self, container: Container) -> Any:
        pass
