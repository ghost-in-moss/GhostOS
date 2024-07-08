from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Dict, Union, Optional, Any, Type, Callable
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class Import(BaseModel):
    """
    import 各种库.
    """
    module: str
    spec: str
    alias: Optional[str]
    description: Optional[str] = Field(default=None)

    def get_name(self) -> str:
        if self.alias:
            return self.alias
        return self.spec

    def get_import_path(self) -> str:
        return self.module + ":" + self.spec


VARIABLE_TYPES = Union[str, int, float, bool, None, List, Dict]


class Define(BaseModel):
    """
    可以在上下文中声明的变量.
    """
    desc: Optional[str] = Field(default=None)
    value: VARIABLE_TYPES = Field(default=None, description="")
    model: Optional[str] = Field(
        default=None,
        description="如果是 pydantic 等类型, 可以通过类进行封装. 类应该在 imports 或者 defines 里.",
    )


# --- python context that transportable --- #

class PyContext(BaseModel):
    """
    可传输的 python 上下文.
    不需要全部用 pickle 之类的库做序列化, 方便管理 bot 的思维空间.
    """

    imports: Dict[str, Import] = Field(default_factory=dict, description="通过 python 引入的包, 类, 方法 等.")
    defines: Dict[str, Define] = Field(default_factory=list, description="在上下文中定义的变量.")

    def join(self, ctx: "PyContext") -> "PyContext":
        """
        合并两个 python context, 以右侧的为准.
        """
        imported = {}
        imports = []

        def append_imports(importing: Import):
            path = importing.get_import_path()
            if path not in imported:
                imported[path] = importing
                imports.append(importing)

        for i in ctx.imports:
            append_imports(i)

        for i in self.imports:
            append_imports(i)

        # codes = ctx.codes
        # if codes is None:
        #     codes = self.codes

        defined_vars = {}
        vars_list = []

        def append_vars(var: Define):
            if var.name not in defined_vars:
                defined_vars[var.name] = var
                vars_list.append(var)

        for v in ctx.defines:
            append_vars(v)

        for v in self.defines:
            append_vars(v)

        return PyContext(imports=imports, variables=vars_list)


class PyLocals:

    def __init__(
            self,
            *,
            values: Optional[Dict[str, Any]] = None,
            classes: Optional[List[Type[object]]] = None,
            libraries: Optional[List[object]] = None,
            functions: Optional[List[Callable]] = None,
            interfaces: Optional[List[Type[object]]] = None,
    ):
        self.values: Optional[Dict[str, Any]] = values
        """直接引入上下文的变量."""

        self.classes: Optional[List[Type[object]]] = classes
        """引入上下文中, 可以实例化的类. """

        self.libraries: Optional[List[object]] = libraries
        """引入上下文中的库, 会添加到 os 里被 LLM 调用. """

        self.functions: Optional[List[Callable]] = functions
        """直接引入上下文中的函数."""

        self.interfaces: Optional[List[Type[object]]] = interfaces
        """上下文中使用的抽象. """
