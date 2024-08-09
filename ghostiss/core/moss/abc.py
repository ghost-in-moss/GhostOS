from typing import Dict, Any, Union, List, Optional, NamedTuple, Type, Callable
from types import ModuleType
from abc import ABC, abstractmethod
from ghostiss.container import Container, Provider, Factory, provide
from ghostiss.core.moss.pycontext import PyContext, attr
from ghostiss.core.moss.prompts import (
    AttrPrompts, reflect_module_locals, PROMPT_MAGIC_ATTR,
    compile_attr_prompts,
)
from ghostiss.core.moss.decorators import cls_source_code

"""
MOSS 是 Model-oriented Operating System Simulation 的简写. 
它将系统当前上下文的 API 通过全代码的方式 Prompt 给模型, 让模型直接生成代码并且执行. 

MOSS 通过 PyContext 来定义一个可持久化, 可以复原的上下文. 
可以在多轮对话, 或者多轮思考中, 反复还原这个上下文. 

使用 moss 的完整生命周期的伪代码如下 (系统会自动集成)

# 第一步, 获取 MOSSCompiler 对象. 
compiler: MOSSCompiler = container.force_fetch(MOSSCompiler)

# 第二步, compiler 可以预定义 Module 的一些内部方法比如 __import__, 或 join pycontext, 然后 compile
# 关于 __import__, 默认会使用 moss.libraries.Modules 的实现. 

runtime: MOSSRuntime = compiler.compile(modulename)

# 这个阶段会编译 pycontext.module 到一个临时的 Module 中, 并对生成的 MOSSRuntime 进行初始化. 
# 如果 pycontext.code 存在, 则使用这个 code. 这是为了支持未来 llm 直接修改上下文, 存一个自己的临时副本. 

# 第三步, 生成 context 的 prompt. 
prompt = runtime.prompter().moss_context_prompt()

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
    'Moss', 'attr',
    'MossCompiler', 'MossRuntime',
    'MossResult', 'MossPrompter',
    'AttrPrompts',
    'MOSS_COMPILE_EVENT', 'MOSS_PROMPT_EVENT', 'MOSS_EXEC_EVENT', 'MOSS_ATTR_PROMPTS_EVENT',
    'MOSS_TYPE_NAME', 'MOSS_NAME',
    'MOSS_HIDDEN_MARK', 'MOSS_HIDDEN_UNMARK',
]

MOSS_COMPILE_EVENT = "__moss_compile__"
"""moss 编译阶段的回调事件, 可以在对应文件里自定义这个事件, 替换系统默认. """

MOSS_ATTR_PROMPTS_EVENT = "__moss_attr_prompts__"
"""通过这个属性来获取一个实例 (module/instance of class) 所有属性的 prompts. """

MOSS_PROMPT_EVENT = "__moss_prompt__"
""" moss 生成 prompt 阶段的回调事件. """

MOSS_EXEC_EVENT = "__moss_exec__"
""" moss 执行阶段的回调事件. """

MOSS_TYPE_NAME = "Moss"

MOSS_NAME = "moss"

MOSS_HIDDEN_MARK = "# <moss>"
""" pycontext.module 源码某一行以这个标记开头, 其后的代码都不生成到 prompt 里. """

MOSS_HIDDEN_UNMARK = "# </moss>"
""" pycontext.module 源码某一行以这个标记开头, 其后的代码都展示到 prompt 里. """


@cls_source_code()
class Moss(ABC):
    """
    Language Model-oriented Operating System Simulation.
    Full python code interface for large language models in multi-turns chat or thinking.
    The property with SerializeType will persist during multi-turns.
    SerializeType means: int, float, str, None, list, dict, BaseModel, TypedDict
    You can edit them if you need.
    """
    pass


#    @abstractmethod
#    def var(
#            self,
#            name: str,
#            value: SerializableType,
#            desc: Optional[str] = None,
#            force: bool = False,
#    ) -> bool:
#        """
#        You can define a serializable value and bind it to moss attributes.
#        Once defined, you can reassign it any time, the attribute value will automatically save in multi-turns.
#        :param name: the attribute name in the moss
#        :param value: the value of the attribute
#        :param desc: the description of the attribute
#        :param force: force overwrite existing attribute
#        :return: False if already defined, otherwise True
#        :exception: TypeError if value is not SerializableType
#        """
#        pass

#    @abstractmethod
#    def inject(self, modulename: str, **specs: str) -> None:
#        """
#        You can inject values from module or its attributes (if specs given) to the MOSS object attributes.
#        The injections of attributes will persist in multi-turns chat or thinking.
#        for example:
#        `moss.inject('module.submodule', 'attr_name'='module_attr_name')`
#
#        equals:
#        `def inject(moss: MOSS):
#            from module.sub_module import module_attr_name as var
#            setattr(moss, 'attr_name', var)
#        inject(moss)
#        assert hasattr(moss, 'attr_name')`
#
#        :exception: NamedError if duplicated attribute name
#        """
#        pass


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
        if self.__compiling__:
            raise RuntimeError('recursively calling compile method')
        if self.__compiled__:
            raise RuntimeError('compiler already compiled')
        self.__compiling__ = True
        try:
            # 使用 locals 和 pycontext.module 对应的代码, 生成 ModuleType.
            module = self._compile(modulename)
            # 在生成的 ModuleType 里查找魔术方法, 提供 provider 等, 为依赖注入做准备.
            if hasattr(module, MOSS_COMPILE_EVENT):
                # 完成编译 moss_compiled 事件.
                # 可以在这个环节对 MOSS 做一些依赖注入的准备.
                fn = getattr(module, MOSS_COMPILE_EVENT)
                fn(self)
            runtime = self._new_runtime(module)
            return runtime
        finally:
            self.__compiling__ = False
            self.__compiled__ = True
            # 手动管理一下, 避免外部解决内存泄漏的心智成本.
            self.destroy()

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
    def destroy(self) -> None:
        """
        主动做垃圾回收的准备, 避免 python 内存泄漏.
        """
        pass


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
    def pycontext_code(
            self,
            model_visible: bool = True,
    ) -> str:
        """
        返回通过 pycontext.module 预定义的代码.
        第一行应该是 from __future__ import annotations. 解决上下文乱续的提示问题.
        :param model_visible: 如果为 True, 只返回大模型可以阅读的代码.
        """
        pass

    def pycontext_attr_prompts(self, excludes: Optional[set] = None) -> AttrPrompts:
        """
        结合已编译的本地变量, 用系统自带的方法反射出上下文属性的 prompts.
        """
        module = self.module()
        name = module.__name__
        local_values = module.__dict__
        yield from reflect_module_locals(name, local_values, excludes=excludes)

    def pycontext_code_prompt(self, auto_generation: bool = True) -> str:
        """
        基于 pycontext code 生成的 Prompt. 用来描述当前上下文里的各种变量.
        主要是从其它库引入的变量.
        :return: 用 python 风格描述的上下文变量.
        """
        done = {}
        names = []
        # 查看是否有源码自带的魔术方法.
        module = self.module()
        if hasattr(module, MOSS_ATTR_PROMPTS_EVENT):
            fn = getattr(module, MOSS_ATTR_PROMPTS_EVENT)
            predefined_prompts: AttrPrompts = fn()
            for name, prompt in predefined_prompts:
                if name and name not in done:
                    names.append(name)
                done[name] = prompt

        # 合并系统自动生成的.
        if auto_generation:
            attr_prompts = self.pycontext_attr_prompts(excludes=set(names))
            for name, prompt in attr_prompts:
                if name not in done:
                    names.append(name)
                done[name] = prompt

        # 保证一下顺序.
        prompts = [(name, done[name]) for name in names]
        return compile_attr_prompts(prompts)

    def dump_context_prompt(self) -> str:
        """
        获取 MOSS 运行时的完整 Python context 的 Prompt.
        这个 Prompt 包含以下几个部分:
        1. predefined_code: 通过 pycontext.module 默认加载的代码 (对大模型可展示的部分).
        2. code_prompt: 对 predefined code 里各种引用类库的描述 prompt. 会包裹在 `\"""` 中展示.
        3. moss_prompt: moss 会注入到当前上下文里, 因此会生成 MOSS Prompt.
        """
        compiled = self.module()
        # 使用目标 module 自带的 prompt, 不做任何干预.
        if PROMPT_MAGIC_ATTR in compiled.__dict__:
            fn = compiled.__dict__[PROMPT_MAGIC_ATTR]
            return fn()
        # 基于 moss prompter 来生成.
        if hasattr(compiled, MOSS_PROMPT_EVENT):
            fn = getattr(compiled, MOSS_PROMPT_EVENT)
            return fn(self)
        from ghostiss.core.moss.lifecycle import __moss_prompt__
        return __moss_prompt__(self)


class MossRuntime(ABC):
    @abstractmethod
    def container(self) -> Container:
        """
        MOSS 使用的依赖注入容器.
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
    def moss(self) -> object:
        """
        基于上下文生成的 MOSS. 依赖注入已经完成.
        """
        pass

    def moss_type(self) -> Type:
        """
        get defined MOSS type
        :return: MOSS class
        """
        module = self.module()
        if MOSS_TYPE_NAME in module.__dict__:
            return module.__dict__[MOSS_TYPE_NAME]
        return Moss

    @abstractmethod
    def dump_context(self) -> PyContext:
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
    def runtime_ctx(self):
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
            args: Optional[List[str]] = None,
            kwargs: Optional[Dict[str, str]] = None,
    ) -> "MossResult":
        """
        基于 moos 提供的上下文, 运行一段代码.
        :param code: 需要运行的代码.
        :param target: 指定上下文中一个变量名用来获取返回值. 如果为空, 则返回 None. 如果是一个方法, 则会运行它.
        :param args: 如果 args 不为 None, 则认为 target 是一个函数, 并从 locals 里指定参数
        :param kwargs: 类似 args
        :return: 根据 result_name 从 code 中获取返回值.
        :exception: any exception will be raised, handle them outside
        """
        if self.__executing__:
            raise RuntimeError(f"Moss already executing")
        try:
            self.__executing__ = True
            compiled = self.module()
            fn = None
            with self.runtime_ctx():
                # 使用 module 自定义的 exec
                if hasattr(compiled, MOSS_EXEC_EVENT):
                    fn = getattr(compiled, MOSS_EXEC_EVENT)
                if fn is None:
                    from ghostiss.core.moss.lifecycle import __moss_exec__
                    fn = __moss_exec__
                # 使用系统默认的 exec
                return fn(self, target=target, code=code, args=args, kwargs=kwargs)
        finally:
            self.__executing__ = False

    def destroy(self) -> None:
        """
        方便垃圾回收.
        """
        pass


class MossResult(NamedTuple):
    """
    result of the moss runtime execution.
    """
    returns: Any
    std_output: str
    pycontext: PyContext
