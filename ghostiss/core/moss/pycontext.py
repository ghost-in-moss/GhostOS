from __future__ import annotations
from typing import Dict, Any, Union, List, Optional, Tuple, TypedDict, NamedTuple
from types import ModuleType
import inspect
from pydantic import BaseModel, Field
from ghostiss.helpers import parse_import_module_and_spec, import_from_str, join_import_module_and_spec


# --- python context that transportable --- #

class PyContext(BaseModel):
    """
    MOSS 运行依赖的 python 上下文.
    """

    module: Optional[str] = Field(
        default=None,
        description="the module path from which import the moss context predefined code",
    )
    code: Optional[str] = Field(
        default=None,
        description="if code given, use it instead of code from the module",
    )

    injections: Dict[str, Injection] = Field(
        default_factory=dict,
        description="通过 python 引入的包, 类, 方法 等. 会注入到 MOSS 上, 同时会实现它.",
    )
    properties: Dict[str, Property] = Field(
        default_factory=dict,
        description="在上下文中定义的变量. 会注入到 MOSS 上. 修改后也会保存到 pycontext 里. ",
    )

    def inject(self, injected: "Injection") -> None:
        self.injections[injected.import_from] = injected

    def define(self, d: "Property") -> None:
        self.properties[d.name] = d

    def join(self, ctx: "PyContext") -> "PyContext":
        """
        合并两个 python context, 以右侧的为准. 并返回一个新的 PyContext 对象. 避免左向污染.
        """
        copied = self.model_copy(deep=True)
        if ctx.module:
            copied.module = ctx.module
        if ctx.code:
            copied.code = ctx.code
        for imp in ctx.injections.values():
            copied.inject(imp)
        for var in ctx.properties.values():
            copied.define(var)
        return copied


class Injection(BaseModel):
    """
    from module import specific attribute then inject to MOSS Context
    """
    import_from: str = Field(
        description="the imported module name or use module path pattern such as 'modulename:attr_name'",
    )
    alias: Optional[str] = Field(default=None, description="context attr alias for the imported value")

    @classmethod
    def reflect(cls, value: Any, alias: Optional[str] = None) -> "Injection":
        """
        reflect a value and generate Imported value.
        :param value:
        :param alias:
        :return:
        """
        modulename = inspect.getmodule(value).__name__
        if inspect.ismodule(value):
            spec = None
        else:
            spec = getattr(value, '__name__', None)
        import_from = join_import_module_and_spec(modulename, spec)
        return Injection(
            import_from=import_from,
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
        return parse_import_module_and_spec(self.import_from)


SerializableType = Union[str, int, float, bool, None, list, dict, BaseModel, TypedDict]
"""系统支持的各种可序列化类型, 可以被存储到 Serializable 里. 更多情况下可以用别的变量类型. """
SerializableData = Union[str, int, float, bool, None, List, Dict]


class Property(BaseModel):
    """
    可以在 MOSS 上下文中声明的变量.
    """
    name: str = Field(description="property name in the moss context")
    desc: str = Field(default="", description="describe the property's purpose")
    value: SerializableType = Field(default=None, description="the serializable value")
    model: Optional[str] = Field(
        default=None,
        description="如果是 pydantic 等类型, 可以通过类进行封装. 类应该在 imports 或者 defines 里.",
    )

    @classmethod
    def from_value(cls, name: str, value: SerializableType, desc: str = "") -> Optional["Property"]:
        p = cls(name=name, desc=desc)
        p.set_value(value)
        return p

    def set_value(self, value: Any) -> None:
        if not isinstance(value, SerializableType):
            # 赋值的时候报错.
            raise AttributeError(f"{value} is not property serializable type {SerializableType}")
        model = None
        has_model = (
                value is not None and isinstance(value, BaseModel)
                or isinstance(value, TypedDict)
        )
        if has_model:
            model = inspect.getmodule(value).__name__ + ':' + type(value).__name__
        if isinstance(value, BaseModel):
            value = value.model_dump(exclude_defaults=True)
        self.value = value
        self.model = model

    def generate_value(self, module: ModuleType) -> Any:
        model = self.model
        value = self.value
        if model is None:
            return value
        elif isinstance(value, Dict):
            modulename, spec = parse_import_module_and_spec(model)
            if modulename == module.__name__:
                cls = module.__dict__.get(modulename, None)
            else:
                cls = import_from_str(model)
            if cls is None:
                # 防止错误的上下文导致阻塞死.
                self.value = None
                return None
            return cls(**value)
        else:
            return None
