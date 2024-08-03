from typing import Dict, Any, Union, List, Optional, Tuple
from abc import ABC, abstractmethod
from ghostiss.container import Container
from pydantic import BaseModel, Field
import inspect


class MOSS(ABC):
    """
    language Model-oriented Operating System Simulation
    full python code interface for large language models
    """

    @abstractmethod
    def imports(self, module: str, *specs: str, **aliases: str) -> Dict[str, Any]:
        """
        You are not allowed to use `from ... import ...` grammar, but use this method instead.
        Replace from ... import ... as ...
        :param module: module name
        :param specs: module spec
        :param aliases: alias=module spec
        :return: values mapped by name to value

        example:
        'from module.a import Foo, Bar as bar'
        could be .imports('module.a', 'Foo', bar='Bar')
        """
        pass

    @abstractmethod
    def define(
            self,
            name: str,
            value: Union[str, int, float, bool, Dict, List, BaseModel],
            desc: Optional[str] = None,
    ) -> Any:
        """
        定义一个变量, 这个变量会保留到下一轮会话中.
        :param name:
        :param value:
        :param desc:
        :return:
        """
        pass

    @abstractmethod
    def print(self, *args, **kwargs) -> None:
        """
        replace builtin print, output will add to next message.
        """
        pass


#
# class MetaMOSS(ABC):
#
#     @abstractmethod
#     def append_code(self, code: str) -> None:
#         pass
#
#     @abstractmethod
#     def update_code(self, regex_pattern: str, replacement: str) -> None:
#         pass


class Injection(BaseModel):
    """
    from module import specific attribute then inject to MOSS Context
    """
    module: str = Field(description="the imported module name")
    spec: Optional[str] = Field(default=None, description="the specific attribute name from the module")
    alias: Optional[str] = Field(default=None, description="context alias for the imported value")

    @classmethod
    def parse(cls, value: Any, alias: Optional[str] = None) -> "Injection":
        modulename = inspect.getmodulename(value)
        if inspect.ismodule(value):
            spec = None
        else:
            spec = getattr(value, '__name__', None)
        return Injection(
            module=modulename,
            spec=spec,
            alias=alias,
        )

    def get_name(self) -> str:
        if self.alias:
            return self.alias
        _, spec = self.get_module_and_spec()
        return spec

    def get_module_and_spec(self) -> Tuple[str, Optional[str]]:
        if self.spec:
            return self.module, self.spec
        return parse_import_module_and_spec(self.module)

    def get_import_path(self) -> str:
        module, spec = self.get_module_and_spec()
        spec = ":" + spec if spec else ""
        return module + spec


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

    module: Optional[str] = Field(default=None, description="")
    injections: List[Injection] = Field(default_factory=list, description="通过 python 引入的包, 类, 方法 等.")
    variables: List[Variable] = Field(default_factory=list, description="在上下文中定义的变量.")

    def add_import(self, imp: Injection) -> None:
        imports = []
        done = False
        for _imp in self.injections:
            if _imp.get_name() == imp.get_name():
                imports.append(imp)
                done = True
            else:
                imports.append(_imp)
        if not done:
            imports.append(imp)
        self.injections = imports

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

        def append_imports(importing: Injection):
            path = importing.get_import_path()
            if path not in imported:
                imported[path] = importing
                imports.append(importing)

        for i in ctx.injections:
            append_imports(i)

        for i in self.injections:
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


class MOSSBuilder(ABC):
    """
    language Model-oriented Operating System Simulation
    full python code interface for large language models
    """

    # --- 创建 MOSS 的方法 --- #
    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    def injects(self, *named_vars, **variables) -> "MOSSBuilder":
        pass

    @abstractmethod
    def join_context(self, context: PyContext) -> "MOSSBuilder":
        """
        为 MOSS 添加更多的变量, 可以覆盖掉之前的.
        :param context:
        :return:
        """
        pass

    @abstractmethod
    def compile(self) -> "MOSSModule":
        pass


class MOSSModule(ABC):

    @abstractmethod
    def moss(self) -> MOSS:
        pass

    @abstractmethod
    def dump_locals(self) -> Dict[str, Any]:
        """
        返回 moss 运行时的上下文变量, 可以结合 exec 提供 locals 并且运行.
        """
        pass

    @abstractmethod
    def execute(
            self,
            *,
            code: str,
            target: str = "",
            args: Optional[List[str]] = None,
            kwargs: Optional[Dict[str, str]] = None,
            update_locals: Optional[Dict[str, Any]] = None,
    ) -> MOSSResult:
        """
        基于 moos 提供的上下文, 运行一段代码.
        :param code: 需要运行的代码.
        :param target: 指定一个变量名用来获取返回值. 如果为空, 则返回 None. 如果是一个方法, 则会运行它.
        :param args: 如果 args 不为 None, 则认为 target 是一个函数, 并从 locals 里指定参数
        :param kwargs: 类似 args
        :param update_locals: 额外添加到上下文里的 locals 变量. 但这些变量不会生成 code prompt.
        :return: 根据 result_name 从 code 中获取返回值.
        :exception: any exception will be raised, handle them outside
        """
        pass


class MOSSResult(ABC):

    @abstractmethod
    def dump_context(self) -> PyContext:
        """
        返回当前的可存储上下文.
        """
        pass

    @abstractmethod
    def dump_code_prompt(self) -> str:
        """
        获取可以描述相关上下文变量的 prompt.
        预期形态为:

        class Contract:
           ...

        class LibType:
           ...

        def caller1():
           ...

        class MOSS(ABC):
           '''
           注解
           '''

           var1: typehint
           ''' var 1 desc '''

           var2: typehint
           ''' var 2 desc'''

           lib1: LibType
        """
        pass

    def destroy(self) -> None:
        """
        方便垃圾回收.
        """
        pass
