from __future__ import annotations
from typing import Dict, Any, Optional, Tuple, Iterator
from types import ModuleType
from pydantic import BaseModel, Field
from ghostos_common.entity import EntityMeta, to_entity_meta, from_entity_meta, is_entity_type

__all__ = [
    'PyContext',
]


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

    # injections: Dict[str, Injection] = Field(
    #     default_factory=dict,
    #     description="通过 python 引入的包, 类, 方法 等. 会注入到 MOSS 上, 同时会实现它.",
    # )

    properties: Dict[str, EntityMeta] = Field(
        default_factory=dict,
    )

    # properties: Dict[str, Property] = Field(
    #     default_factory=dict,
    #     description="在上下文中定义的变量. 会注入到 MOSS 上. 修改后也会保存到 pycontext 里. ",
    # )

    execute_code: Optional[str] = Field(
        default=None,
        description="the generated python code on this context",
    )

    executed: bool = Field(
        default=False,
        description="if the generated code is executed",
    )

    def set_prop(self, name: str, value: Any):
        self.properties[name] = to_entity_meta(value)

    def get_prop(self, name: str, module: Optional[ModuleType] = None) -> Any:
        if name not in self.properties:
            return None
        value = self.properties[name]
        return from_entity_meta(value, module)

    @staticmethod
    def allow_prop(value: Any) -> bool:
        if isinstance(value, BaseModel):
            return True
        elif isinstance(value, bool):
            return True
        elif isinstance(value, str):
            return True
        elif isinstance(value, int):
            return True
        elif isinstance(value, float):
            return True
        elif isinstance(value, list):
            return True
        elif isinstance(value, dict):
            return True
        elif is_entity_type(value):
            return True
        return False

    def iter_props(self, module: Optional[ModuleType] = None) -> Iterator[Tuple[str, Any]]:
        for name in self.properties:
            value = self.properties[name]
            yield name, from_entity_meta(value, module)

    def join(self, ctx: "PyContext") -> "PyContext":
        """
        合并两个 python context, 以右侧的为准. 并返回一个新的 PyContext 对象. 避免左向污染.
        """
        copied = self.model_copy(deep=True)
        if copied.module is None:
            copied.module = ctx.module
        if copied.code is None:
            copied.code = ctx.code
        if copied.execute_code is None:
            copied.execute_code = ctx.execute_code
            copied.executed = ctx.executed

        for key, val in ctx.properties.items():
            copied.properties[key] = val
        return copied

# class Injection(BaseModel):
#     """
#     from module import specific attribute then inject to MOSS Context
#     """
#     import_from: str = Field(
#         description="the imported module name or use module path pattern such as 'modulename:attr_name'",
#     )
#     alias: Optional[str] = Field(default=None, description="context attr alias for the imported value")
#
#     @classmethod
#     def reflect(cls, value: Any, alias: Optional[str] = None) -> "Injection":
#         """
#         reflect a value and generate Imported value.
#         :param value:
#         :param alias:
#         :return:
#         """
#         modulename = inspect.getmodule(value).__name__
#         if inspect.ismodule(value):
#             spec = None
#         else:
#             spec = getattr(value, '__name__', None)
#         import_from = join_import_module_and_spec(modulename, spec)
#         return Injection(
#             import_from=import_from,
#             alias=alias,
#         )
#
#     def get_name(self) -> str:
#         if self.alias:
#             return self.alias
#         _, spec = self.get_from_module_attr()
#         return spec
#
#     def get_from_module_attr(self) -> Tuple[str, Optional[str]]:
#         """
#         :return: modulename and attribute name from the module
#         """
#         return parse_import_module_and_spec(self.import_from)
#
#
# SerializableType = Union[str, int, float, bool, None, list, dict, BaseModel, TypedDict]
# """系统支持的各种可序列化类型, 可以被存储到 Serializable 里. 更多情况下可以用别的变量类型. """
# SerializableData = Union[str, int, float, bool, None, List, Dict]
#
#
# class Property(BaseModel):
#     """
#     可以在 MOSS 上下文中声明的变量.
#     """
#     name: str = Field(default="", description="property name in the moss context")
#     desc: str = Field(default="", description="describe the property's purpose")
#     value: Union[str, int, float, bool, None, list, dict, BaseModel, TypedDict] = Field(
#         default=None,
#         description="the serializable value",
#     )
#     model: Optional[str] = Field(
#         default=None,
#         description="如果是 pydantic 等类型, 可以通过类进行封装. 类应该在 imports 或者 defines 里.",
#     )
#
#     def __set_name__(self, owner, name):
#         self.name = name
#         if hasattr(owner, '__pycontext__') and isinstance(owner.__pycontext__, PyContext):
#             owner.__pycontext__.define(self)
#
#     def __set__(self, instance, value):
#         if value is self:
#             return
#         if isinstance(value, Property):
#             self.value = value.value
#             self.model = value.model
#             self.name = value.name
#             self.model = value.model
#         self.set_value(value)
#
#     def __get__(self, instance, owner):
#         return self.generate_value()
#
#     def __delete__(self):
#         self.__value__ = None
#         self.value = None
#         self.model = None
#
#     @classmethod
#     def from_value(cls, *, name: str = "", value: SerializableType, desc: str = "") -> Optional["Property"]:
#         p = cls(name=name, desc=desc)
#         p.set_value(value)
#         return p
#
#     def set_value(self, value: Any) -> None:
#         if not isinstance(value, SerializableType):
#             # 赋值的时候报错.
#             raise AttributeError(f"{value} is not property serializable type {SerializableType}")
#         model = None
#         has_model = (
#                 value is not None and isinstance(value, BaseModel)
#                 or is_typeddict(value)
#         )
#         if has_model:
#             type_ = type(value)
#             if type_.__qualname__:
#                 model = type_.__module__ + ':' + type_.__qualname__
#             else:
#                 model = type_.__module__ + ':' + type_.__name__
#         self.value = value
#         self.model = model
#
#     def generate_value(self, module: Optional[ModuleType] = None) -> Any:
#         model = self.model
#         value = self.value
#         if isinstance(self.value, dict) and model is not None:
#             if not isinstance(value, Dict):
#                 raise AttributeError(f"'{value}' is not dict while model class is '{model}'")
#             cls = None
#             if module is not None:
#                 modulename, spec = parse_import_module_and_spec(model)
#                 if modulename == module.__name__:
#                     # 用这种方法解决临时模块里的变量问题.
#                     cls = get_module_spec(module.__dict__, spec)
#             if cls is None:
#                 cls = import_from_path(model)
#             if issubclass(cls, BaseModel):
#                 self.value = cls(**value)
#         return self.value
#
#
# @definition()
# def attr(
#         default: SerializableType = None, *,
#         default_factory: Optional[Callable[[], Any]] = None,
#         desc: str = "",
# ) -> SerializableType:
#     """
#     用于定义一个要绑定到 MOSS 上的属性, 它的值可以在多轮对话和思考过程中保存和修改.
#     :param default: 属性的默认值, 目前支持 str, int, float, bool, None, list, dict, BaseModel, TypedDict
#     :param default_factory: 可以传入一个 lambda 或闭包, 当 default 为 None 时生成值.
#     :param desc: 属性的描述.
#     """
#     if default is None and default_factory:
#         default = default_factory()
#     return Property.from_value(value=default, desc=desc)
