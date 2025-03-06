from __future__ import annotations
from typing import Dict, Any, Union, List, Optional, NamedTuple, Type, Callable, TypeVar, ClassVar
from typing_extensions import Self
from types import ModuleType, FunctionType
from abc import ABC, abstractmethod
from ghostos_container import Container, Provider, Factory, provide
from ghostos_moss.pycontext import PyContext
from ghostos_moss.prompts import (
    AttrPrompts, reflect_locals_imported, compile_attr_prompts
)
from ghostos_common.prompter import PromptObjectModel

"""
MOSS 是 Model-oriented Operating System Simulation 的简写. 
它将系统当前上下文的 API 通过全代码的方式 Prompt 给模型, 让模型直接生成代码并且执行. 

MOSS 通过 PyContext 来定义一个可持久化, 可以复原的上下文. 
可以在多轮对话, 或者多轮思考中, 反复还原这个上下文. 

使用 moss 的完整生命周期的伪代码如下 (系统会自动集成)

# 第一步, 获取 MOSSCompiler 对象. 
compiler: MOSSCompiler = container.force_fetch(MOSSCompiler)

# 第二步, compiler 可以预定义 Module 的一些内部方法比如 __import__, 或 join pycontext, 然后 compile
# 关于 __import__, 默认会使用 contracts.modules.Modules 的实现. 

runtime: MOSSRuntime = compiler.join_pycontext(pycontext).compile(modulename)

# 这个阶段会编译 pycontext.module 到一个临时的 Module 中, 并对生成的 MOSSRuntime 进行初始化. 
# 如果 pycontext.code 存在, 则使用这个 code. 这是为了支持未来 llm 直接修改上下文, 存一个自己的临时副本. 

# 第三步, 生成 context 的 prompt. 
prompt = runtime.prompter().dump_context_prompt()

# 第四步, 使用 prompt 生成 chat, 调用大模型或人工生成代码. 
code = llm_runner(prompt)

# 第五步, 将 llm 生成的 code 让 moss runtime 执行, 并指定返回值或调用的方法 (target) 
result: MOSSResult = runtime.execute(code, target=xxxx)

# 第六步, 使用返回值, 并且 destroy()
returns = result.returns
std_output = result.std_output
# 获取需要保存的 pycontext. 
pycontext = result.pycontext

最后记得执行 runtime.destroy(), 否则可能内存泄漏. 
"""

__all__ = [
    'Moss',
    'MossCompiler', 'MossRuntime',
    'Execution', 'MossPrompter',
    # 'moss_message',
    'AttrPrompts',
    'MOSS_TYPE_NAME', 'MOSS_VALUE_NAME',
    'MOSS_HIDDEN_MARK', 'MOSS_HIDDEN_UNMARK',
    'Injection',
    'SelfUpdater',
]

MOSS_TYPE_NAME = "Moss"

MOSS_VALUE_NAME = "moss"

MOSS_HIDDEN_MARK = "# <moss-hide>"
""" pycontext.module 源码某一行以这个标记开头, 其后的代码都不生成到 prompt 里. """

MOSS_HIDDEN_UNMARK = "# </moss-hide>"
""" pycontext.module 源码某一行以这个标记开头, 其后的代码都展示到 prompt 里. """


class Moss(ABC):
    """
    Language Model-oriented Operating System Simulator.
    Python interface of Runtime Injections for AI-Models in multi-turns chat or thinking.
    * The members with typehint will be injected with runtime instances.
    * The property of SerializeType will persist during multi-turns.
    * SerializeType: int, float, str, None, list, dict, BaseModel, TypedDict
    """

    T = TypeVar('T')

    executing_code: Optional[str]
    """the code that execute the moss instance."""

    __watching__: List[Union[FunctionType, ModuleType, type]] = []
    """the class or module that dose not bound to moss but still want to watch the interface of them"""

    __ignored__: List[str] = []
    """the ignored module names that do not need to watch the code interface of them"""

    @abstractmethod
    def pprint(self, *args, **kwargs) -> None:
        """
        pretty print
        """
        pass


class Injection(ABC):
    """
    the hook interface for classes that bound to Moss
    when inject into the moss instance, on_inject will be called.
    when moss instance destroyed, on_destroy will be called.
    """

    @abstractmethod
    def on_inject(self, runtime: MossRuntime, property_name: str) -> Self:
        pass

    @abstractmethod
    def on_destroy(self) -> None:
        pass


class MossCompiler(ABC):
    """
    language Model-oriented Operating System Simulation
    full python code interface for large language models
    """

    # --- 创建 MOSS 的方法 --- #
    @abstractmethod
    def container(self) -> Container:
        """
        MOSS 专用的 IoC 容器.
        用来给 moss 实例实现依赖注入.
        """
        pass

    @abstractmethod
    def with_default_moss_type(self, moss_type: Union[Type[Moss], str]) -> Self:
        """
        with default moss type if the Moss subclass is not defined at the module.
        """
        pass

    @abstractmethod
    def pycontext(self) -> PyContext:
        """
        MOSS 的动态上下文, 可以序列化保存到历史消息里, 从而在分布式系统里重新还原上下文.
        """
        pass

    @abstractmethod
    def join_context(self, context: PyContext) -> "MossCompiler":
        """
        为 MOSS 上下文添加一个可以持久化存储的 context 变量, 合并默认值.
        :param context:
        :return:
        """
        pass

    @abstractmethod
    def pycontext_code(self) -> str:
        """
        返回通过 pycontext.module 预定义的代码.
        """
        pass

    @abstractmethod
    def with_locals(self, **kwargs) -> "MossCompiler":
        """
        人工添加一些 locals 变量, 到目标 module 里. 在编译之前就会加载到目标 ModuleType.
        主要解决 __import__ 之类的内置方法, 如果必要的话.
        :param kwargs: locals
        :return: self
        """
        pass

    @abstractmethod
    def with_ignored_imported(self, module_names: List[str]) -> "MossCompiler":
        """
        ignored module names will not be prompt from imported attrs
        """
        pass

    def register(self, provider: Provider) -> None:
        """
        向生成 MOSS 的 IoC 容器里注册 Provider.
        当 MOSS 的属性定义了
        :param provider:
        :return:
        """
        self.container().register(provider)

    def bind(self, abstract: Any, value: Union[Factory, Any]) -> None:
        """
        向生成 MOSS 的 IoC 容器里注册工厂方法或实现.
        :param abstract: 抽象定义, 用来获取 value.
        :param value: 可以是一个值, 或者是一个 Factory. 如果是 Factory 的话, 取值的时候会使用它来做实例化.
        # todo: 具体实现可以记录日志.
        """
        if isinstance(value, Callable):
            provider = provide(abstract, singleton=False)(value)
            self.container().register(provider)
        else:
            self.container().set(abstract, value)

    @abstractmethod
    def injects(
            self,
            **attrs: Any,
    ) -> "MossCompiler":
        """
        inject certain values to the MOSS.
        Will automatically bind certain attributes to the MOSS instance (setattr).
        :param attrs: attr_name to attr_value (better with prompt)
        """
        pass

    __compiling__: bool = False
    __compiled__: bool = False

    def compile(
            self,
            modulename: Optional[str],
    ) -> "MossRuntime":
        """
        正式编译出一个 MOSSRuntime. 每一个 Compiler 只能编译一次.
        :param modulename: 生成的 ModuleType 所在的包名. 相关代码会在这个临时 ModuleType 里生成. 如果 modulename为空, 则使用原来的
        """
        from ghostos_moss.lifecycle import __moss_compile__
        if self.__compiling__:
            raise RuntimeError('recursively calling compile method')
        if self.__compiled__:
            raise RuntimeError('compiler already compiled')
        self.__compiling__ = True
        try:
            # 使用 locals 和 pycontext.module 对应的代码, 生成 ModuleType.
            module = self._compile(modulename)
            # 在生成的 ModuleType 里查找魔术方法, 提供 provider 等, 为依赖注入做准备.
            if hasattr(module, __moss_compile__.__name__):
                # 完成编译 moss_compiled 事件.
                # 可以在这个环节对 MOSS 做一些依赖注入的准备.
                fn = getattr(module, __moss_compile__.__name__)
                fn(self)
            runtime = self._new_runtime(module)
            return runtime
        finally:
            self.__compiling__ = False
            self.__compiled__ = True
            # 手动管理一下, 避免外部解决内存泄漏的心智成本.
            self.close()

    @abstractmethod
    def _compile(self, modulename: Optional[str] = None) -> ModuleType:
        """
        运行 pycontext.module 的代码, 编译 Module.
        """
        pass

    @abstractmethod
    def _new_runtime(self, module: ModuleType) -> "MossRuntime":
        """
        实例化 Runtime.
        :param module:
        :return:
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        主动做垃圾回收的准备, 避免 python 内存泄漏.
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MossPrompter(ABC):
    """
    MOSS 的运行时, 已经完成了第一阶段的编译.
    pycontext.module 的相关代码已经加载.
    这个阶段应该完成 MOSS 本身的注入准备.
    """

    @abstractmethod
    def container(self) -> Container:
        """
        MOSS 使用的依赖注入容器.
        """
        pass

    @abstractmethod
    def module(self) -> ModuleType:
        """
        当前的临时 Module.
        """
        pass

    @abstractmethod
    def get_source_code(
            self,
            exclude_hide_code: bool = True,
    ) -> str:
        """
        返回通过 pycontext.module 预定义的代码.
        第一行应该是 from __future__ import annotations. 解决上下文乱续的提示问题.
        :param exclude_hide_code: 如果为 True, 只返回大模型可以阅读的代码.
        """
        pass

    @abstractmethod
    def get_imported_attrs(self) -> Dict[str, Any]:
        """
        get imported attrs (function, class, or module) of the compiled module
        """
        pass

    @abstractmethod
    def get_imported_attrs_prompt(self, includes: List = None) -> str:
        """
        get the default prompt of the imported attrs.
        :return:
        """
        pass

    @abstractmethod
    def replaced_magic_prompts(self) -> Dict[str, str]:
        """
        the ghostos_moss.magics.MagicPrompter in this compiled module are replaced into str.
        :return: the replaced Dict[attr_name, prompt]
        """
        pass

    def get_magic_prompt(self) -> str:
        prompts = self.replaced_magic_prompts()
        if prompts:
            lines = [f"`{key}`:\n{prompt.strip()}" for key, prompt in prompts.items()]
            return "\n\n".join(lines)
        return ""

    def imported_attr_prompts(self) -> AttrPrompts:
        """
        结合已编译的本地变量, 用系统自带的方法反射出上下文属性的 prompts.
        """
        module = self.module()
        name = module.__name__
        local_values = module.__dict__
        yield from reflect_locals_imported(
            name,
            local_values,
        )

    def dump_imported_prompt(self, auto_generation: bool = True, attr_prompts: Dict[str, str] = None) -> str:
        """
        基于 pycontext code 生成的 Prompt. 用来描述当前上下文里的各种变量.
        主要是从其它库引入的变量.
        :return: 用 python 风格描述的上下文变量.
        """
        from ghostos_moss.lifecycle import __moss_attr_prompts__
        done = attr_prompts if attr_prompts else {}
        names = []
        # 查看是否有源码自带的魔术方法.
        module = self.module()
        if hasattr(module, __moss_attr_prompts__.__name__):
            fn = getattr(module, __moss_attr_prompts__.__name__)
            predefined_prompts: AttrPrompts = fn()
            for name, prompt in predefined_prompts:
                if prompt is None:
                    continue
                if name and name not in done:
                    names.append(name)
                done[name] = prompt

        # 合并系统自动生成的.
        if auto_generation:
            reflected_attr_prompts = self.imported_attr_prompts()
            for name, prompt in reflected_attr_prompts:
                if name not in done:
                    names.append(name)
                    done[name] = prompt

        # 保证一下顺序.
        prompts = [(name, done[name]) for name in names]
        return compile_attr_prompts(prompts)

    def dump_module_prompt(self, attr_prompts: Dict[str, str] = None) -> str:
        """
        获取 MOSS 运行时的完整 Python context 的 Prompt.
        这个 Prompt 包含以下几个部分:
        1. predefined_code: 通过 pycontext.module 默认加载的代码 (对大模型可展示的部分).
        2. pycontext_code_prompt: 对 predefined code 里各种引用类库的描述 prompt. 会包裹在 `\"""` 中展示.
        3. moss_prompt: moss 会注入到当前上下文里, 因此会生成 MOSS Prompt.
        """
        from ghostos_moss.lifecycle import __moss_module_prompt__
        compiled = self.module()
        # 基于 moss prompter 来生成.
        if hasattr(compiled, __moss_module_prompt__.__name__):
            fn = getattr(compiled, __moss_module_prompt__.__name__)
            return fn(self)
        return __moss_module_prompt__(self, attr_prompts)


class MossRuntime(ABC):
    instance_count: ClassVar[int] = 0

    @abstractmethod
    def container(self) -> Container:
        """
        MOSS 使用的依赖注入容器.
        """
        pass

    @abstractmethod
    def lint_exec_code(self, code: str) -> Optional[str]:
        """
        lint execution code and return error info if error occurs
        """
        pass

    @abstractmethod
    def prompter(self) -> MossPrompter:
        """
        返回一个 Prompter, 专门提供 prompt.
        """
        pass

    @abstractmethod
    def module(self) -> ModuleType:
        """
        最终运行的 Module.
        """
        pass

    @abstractmethod
    def locals(self) -> Dict[str, Any]:
        """
        返回运行时的上下文变量.
        其中一定包含 MOSS 类和注入的 moss 实例.
        """
        pass

    @abstractmethod
    def moss_injections(self) -> Dict[str, Any]:
        """
        get injections that bound to moss
        """
        pass

    def get_moss_injected_poms(self) -> Dict[str, PromptObjectModel]:
        """
        get injected PromptObjectModels that bound to moss
        """
        return {name: value for name, value in self.moss_injections().items() if isinstance(value, PromptObjectModel)}

    @abstractmethod
    def moss(self) -> Moss:
        """
        基于上下文生成的 MOSS. 依赖注入已经完成.
        """
        pass

    def moss_type(self) -> Type[Moss]:
        """
        get defined MOSS type
        :return: MOSS class
        """
        module = self.module()
        if MOSS_TYPE_NAME in module.__dict__:
            moss_type = module.__dict__[MOSS_TYPE_NAME]
            if not issubclass(moss_type, Moss):
                raise TypeError(f"Moss type {moss_type} is not subclass of {Moss}")
            return moss_type
        return Moss

    @abstractmethod
    def dump_pycontext(self) -> PyContext:
        """
        返回当前的可存储上下文.
        """
        pass

    @abstractmethod
    def dump_std_output(self) -> str:
        """
        返回重定向 buff 后的 std output
        需要结合 runtime_ctx 来开启 buffer.
        """
        pass

    @abstractmethod
    def redirect_stdout(self):
        """
        with runtime.exec_ctx():
            ...
        :return: a context object that co-operates with `with` statement
        """
        pass

    __executing__: bool = False

    def execute(
            self,
            *,
            target: str,
            code: Optional[str] = None,
            local_args: Optional[List[str]] = None,
            local_kwargs: Optional[Dict[str, str]] = None,
            args: Optional[List[Any]] = None,
            kwargs: Optional[Dict[str, Any]] = None,
    ) -> "Execution":
        """
        基于 moos 提供的上下文, 运行一段代码.
        :param code: 需要运行的代码.
        :param target: 指定上下文中一个变量名用来获取返回值. 如果为空, 则返回 None. 如果是一个方法, 则会运行它.
        :param local_args: 如果 args 不为 None, 则认为 target 是一个函数, 并从 locals 里指定参数
        :param local_kwargs: 类似 args
        :param args: 从外部注入的参数变量
        :param kwargs: 从外部注入的参数变量.
        :return: 根据 result_name 从 code 中获取返回值.
        :exception: any exception will be raised, handle them outside
        """
        from ghostos_moss.lifecycle import __moss_exec__
        self.update_executing_code(code)
        if self.__executing__:
            raise RuntimeError(f"Moss already executing")
        try:
            self.__executing__ = True
            compiled = self.module()
            fn = None
            with self.redirect_stdout():
                # 使用 module 自定义的 exec
                if hasattr(compiled, __moss_exec__.__name__):
                    fn = getattr(compiled, __moss_exec__.__name__)
                if fn is None:
                    fn = __moss_exec__
                # 使用系统默认的 exec
                return fn(
                    self,
                    target=target,
                    code=code,
                    local_args=local_args,
                    local_kwargs=local_kwargs,
                    args=args,
                    kwargs=kwargs,
                )
        finally:
            self.__executing__ = False

    @abstractmethod
    def update_executing_code(self, code: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        """
        方便垃圾回收.
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class Execution(NamedTuple):
    """
    result of the moss runtime execution.
    """
    returns: Any
    std_output: str
    pycontext: PyContext


class SelfUpdater(ABC):
    """
    update moss module code.
    Notice:
    * only after save(), the modified code is wrote to the module's source file.
    * define a function or method without self updater will never be saved to the module.
    * use code string to save, if you use \''' or \""" to embrace them, WATCH CAREFULLY about indent spaces and slashes.
    """

    @abstractmethod
    def append(self, code: str) -> None:
        """
        append code to this module.
        :param code: the code to append.
        """
        pass

    @abstractmethod
    def replace_attr(self, attr_name: str, code: str) -> None:
        """
        replace attr (function or class) in this module.
        """
        pass

    @abstractmethod
    def getsource(self) -> str:
        """
        get origin source of this module.
        """
        pass

    @abstractmethod
    def rewrite(self, code: str) -> None:
        """
        rewrite the whole content of this module.
        """
        pass

    @abstractmethod
    def save(self, reload: bool = True) -> None:
        """
        save the changes of this module to the file.
        :param reload: reload the changes of this module to the current process. otherwise it not work yet.
        """
        pass
