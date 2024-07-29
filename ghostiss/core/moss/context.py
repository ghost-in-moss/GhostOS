from typing import List, Dict, Union, Optional, Any
from pydantic import BaseModel, Field
import inspect

__all__ = [
    'Imported', 'Variable', 'PyContext'
]


class Imported(BaseModel):
    """
    import 各种库.
    """
    module: str = Field(description="the imported module name")
    spec: Optional[str] = Field(default=None, description="the specific attribute name from the module")
    alias: Optional[str] = Field(default=None, description="context alias for the imported value")

    @classmethod
    def parse(cls, value: Any, alias: Optional[str] = None) -> "Imported":
        modulename = inspect.getmodulename(value)
        if inspect.ismodule(value):
            spec = None
        else:
            spec = getattr(value, '__name__', None)
        return Imported(
            module=modulename,
            spec=spec,
            alias=alias,
        )

    def get_name(self) -> str:
        if self.alias:
            return self.alias
        return self.spec

    def get_import_path(self) -> str:
        spec = ":" + self.spec if self.spec else ""
        return self.module + spec


VARIABLE_TYPES = Union[str, int, float, bool, None, List, Dict]


class Variable(BaseModel):
    """
    可以在上下文中声明的变量.
    """
    name: str = Field()
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

    imported: List[Imported] = Field(default_factory=list, description="通过 python 引入的包, 类, 方法 等.")
    variables: List[Variable] = Field(default_factory=list, description="在上下文中定义的变量.")

    def add_import(self, imp: Imported) -> None:
        imports = []
        done = False
        for _imp in self.imported:
            if _imp.get_name() == imp.get_name():
                imports.append(imp)
                done = True
            else:
                imports.append(_imp)
        if not done:
            imports.append(imp)
        self.imported = imports

    def add_define(self, d: Variable) -> None:
        defines = []
        done = False
        for d_ in self.variables:
            if d_.name == d.name:
                defines.append(d)
                done = True
            else:
                defines.append(d_)
        if not done:
            defines.append(d)
        self.variables = defines

    def join(self, ctx: "PyContext") -> "PyContext":
        """
        合并两个 python context, 以右侧的为准. 并返回一个新的 PyContext 对象. 避免左向污染.
        """
        imported = {}
        imports = []

        def append_imports(importing: Imported):
            path = importing.get_import_path()
            if path not in imported:
                imported[path] = importing
                imports.append(importing)

        for i in ctx.imported:
            append_imports(i)

        for i in self.imported:
            append_imports(i)

        # codes = ctx.codes
        # if codes is None:
        #     codes = self.codes

        defined_vars = {}
        vars_list = []

        def append_vars(var: Variable):
            if var.name not in defined_vars:
                defined_vars[var.name] = var
                vars_list.append(var)

        for v in ctx.variables:
            append_vars(v)

        for v in self.variables:
            append_vars(v)

        return PyContext(imported=imports, variables=vars_list)
