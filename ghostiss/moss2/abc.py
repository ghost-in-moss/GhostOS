import inspect
from typing import Dict, Any, Union, List, Optional, NamedTuple, Type, Tuple, Callable, Iterable
from types import ModuleType
from abc import ABC, abstractmethod
from ghostiss.container import Container, Provider, Factory
from ghostiss.moss2.pycontext import PyContext, SerializableType
from ghostiss.moss2.prompts import (
    AttrPrompter, reflect_locals, join_prompt_lines, ATTR_PROMPT_MAGIC_ATTR, PROMPT_MAGIC_ATTR,
)

"""
MOSS 是 Model-oriented Operating System Simulation 的简写. 
它将系统当前上下文的 API 通过全代码的方式 Prompt 给模型, 让模型直接生成代码并且执行. 

MOSS 通过 PyContext 来定义一个可持久化, 可以复原的上下文. 
可以在多轮对话, 或者多轮思考中, 反复还原这个上下文. 

使用 moss 的完整生命周期的伪代码如下 (系统会自动集成)

# 第一步, 获取 MOSSCompiler 对象. 
compiler: MOSSCompiler = container.force_fetch(MOSSCompiler)

# 第二步, compiler 可以预定义 Module 的一些内部方法比如 __import__, 或 join pycontext, 然后 compile
runtime: MOSSRuntime = compiler.compile(xxx)

# 这个阶段会编译 pycontext.module 到一个临时的 Module 中, 并对生成的 MOSSRuntime 进行初始化. 
# runtime 可以用来做依赖注入的准备. 

# 第三步, 生成 context 的 prompt. 
prompt = runtime.moss_context_prompt()

# 第四步, 使用 prompt 生成 chat, 调用大模型或人工生成代码. 
code = llm_runner(prompt)

# 第五步, 将 llm 生成的 code 让 moss runtime 执行, 并指定返回值或调用的方法 (target) 
result: MOSSResult = context.interpret(code, target=xxxx)

# 第六步, 使用返回值, 并且 destroy()
returns = result.returns
std_output = result.std_output
# 获取需要保存的 pycontext. 
pycontext = result.pycontext


"""

__all__ = [
    'MOSS',
    'MOSSCompiler', 'MOSSResult', 'MOSSPrompter', 'MOSSExecutor',
]

AttrPrompts = Iterable[Tuple[str, Optional[str]]]

MOSS_COMPILED_EVENT = "__moss_compiled__"

MOSS_PROMPT_EVENT = "__moss_prompt__"

MOSS_EXEC_EVENT = "__moss_exec__"

MOSS_TYPE_NAME = "MOSS"


class MOSS(ABC):
    """
    Language Model-oriented Operating System Simulation.
    Full python code interface for large language models in multi-turns chat or thinking.
    """

    @abstractmethod
    def var(
            self,
            name: str,
            value: SerializableType,
            desc: Optional[str] = None,
            force: bool = False,
    ) -> bool:
        """
        You can define a serializable value and bind it to moss attributes.
        Once defined, you can reassign it any time, the attribute value will automatically save in multi-turns.
        :param name: the attribute name in the moss
        :param value: the value of the attribute
        :param desc: the description of the attribute
        :param force: force overwrite existing attribute
        :return: False if already defined, otherwise True
        """
        pass

    @abstractmethod
    def inject(self, modulename: str, **specs: str) -> None:
        """
        You can inject values from module or its attributes (if specs given) to the MOSS object attributes.
        The injections of attributes will persist in multi-turns chat or thinking.
        for example:
        `moss.inject('module.submodule', 'attr_name'='module_attr_name')`

        equals:
        `def inject(moss: MOSS):
            from module.sub_module import module_attr_name as var
            setattr(moss, 'attr_name', var)
        inject(moss)
        assert hasattr(moss, 'attr_name')`

        :exception: NamedError if duplicated attribute name
        """
        pass

    @abstractmethod
    def remove(self, name: str) -> None:
        """
        remove an injected or defined attribute from the moss
        :param name: attribute name
        """
        pass


class MOSSCompiler(ABC):
    """
    language Model-oriented Operating System Simulation
    full python code interface for large language models
    """

    # --- 创建 MOSS 的方法 --- #
    @abstractmethod
    def container(self) -> Container:
        """
        MOSS 专用的 IoC 容器.
        会预先注册好上下文相关的一些 Provider 之类的数据.
        """
        pass

    @abstractmethod
    def pycontext(self) -> PyContext:
        """
        MOSS 的动态上下文, 可以序列化保存到历史消息里, 从而在分布式系统里重新还原上下文.
        """
        pass

    @abstractmethod
    def join_context(self, context: PyContext) -> "MOSSCompiler":
        """
        为 MOSS 上下文添加一个可以持久化存储的 context 变量, 合并默认值.
        :param context:
        :return:
        """
        pass

    @abstractmethod
    def with_locals(self, **kwargs) -> "MOSSCompiler":
        """
        人工添加一些 locals 变量, 到目标 module 里. 在编译之前就会加载到目标 ModuleType.
        主要解决 __import__ 之类的方法.
        :param kwargs: locals
        :return: self
        """
        pass

    def compile(
            self,
            modulename: str = "__main__",
    ) -> "MOSSPrompter":
        """
        正式编译出一个 MOSSRuntime.
        :param modulename: 生成的 ModuleType 所在的包名. 相关代码会在这个临时 ModuleType 里生成.
        """
        # 使用 locals 和 pycontext.module 对应的代码, 生成 ModuleType.
        module = self._compile(modulename)
        runtime = self._new_runtime(module)
        # 在生成的 ModuleType 里查找魔术方法, 对 Runtime 进行初始化.
        if MOSS_COMPILED_EVENT in module.__dict__:
            # 完成编译 moss_compiled 事件.
            # 可以在这个环节对 MOSS 做一些依赖注入的准备.
            fn = module.__dict__[MOSS_COMPILED_EVENT]
            return fn(runtime)
        return runtime

    @abstractmethod
    def _compile(self, modulename: str) -> ModuleType:
        """
        运行 pycontext.module 的代码, 编译 Module.
        """
        pass

    @abstractmethod
    def _new_runtime(self, module: ModuleType) -> "MOSSPrompter":
        """
        实例化 Runtime.
        :param module:
        :return:
        """
        pass


class MOSSPrompter(ABC):
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

    def register(self, provider: Provider) -> None:
        """
        向 MOSS 的 IoC 容器里注册 Provider.
        :param provider:
        :return:
        """
        self.container().register(provider)

    def bind(self, abstract: Any, value: Union[Factory, Any]) -> None:
        """
        向 MOSS 的 IoC 容器里注册工厂方法或实现. 
        :param abstract: 抽象
        :param value: 
        :return: 
        """
        self.container().set(abstract, value)

    @abstractmethod
    def injects(
            self,
            **attrs: Any,
    ) -> "MOSSPrompter":
        """
        inject certain values to the MOSS
        :param attrs: attr_name to attr_value (better with prompt)
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

    @abstractmethod
    def local_attr_prompts(self) -> AttrPrompts:
        module = self.module()
        if ATTR_PROMPT_MAGIC_ATTR in module.__dict__:
            fn = module.__dict__[ATTR_PROMPT_MAGIC_ATTR]
            yield from fn()
        else:
            yield from reflect_locals(module.__name__, module.__dict__)

    def pycontext_code_prompt(self) -> str:
        """
        基于 Predefined code 生成的 Prompt.
        :return:
        """
        attr_prompts = self.local_attr_prompts()
        done = {}
        names = []
        for name, prompt in attr_prompts:
            if name not in done:
                names.append(name)
            done[name] = prompt
        prompts = [done[name] for name in names]
        return join_prompt_lines(*prompts)

    def moss_type(self) -> Type:
        """
        get defined MOSS type
        :return: MOSS class
        """
        module = self.module()
        if "MOSS" in module.__dict__:
            t = module.__dict__["MOSS"]
            if not inspect.isclass(t):
                raise TypeError(f"defined MOSS type {t} is not a class")
        return MOSS

    @abstractmethod
    def moss_prompt(self) -> str:
        pass

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
        if MOSS_PROMPT_EVENT in compiled.__dict__:
            fn = compiled.__dict__[MOSS_PROMPT_EVENT]
            return fn(self)
        from ghostiss.moss2.lifecycle import __moss_prompt__
        return __moss_prompt__(self)

    @abstractmethod
    def executor(self) -> "MOSSExecutor":
        pass


class MOSSExecutor(ABC):

    @abstractmethod
    def module(self) -> ModuleType:
        """
        最终运行的 Module.
        """
        pass

    def locals(self) -> Dict[str, Any]:
        """
        返回运行时的上下文变量.
        """
        return self.module().__dict__

    @abstractmethod
    def moss(self) -> object:
        """
        基于上下文生成的 MOSS. 依赖注入已经完成.
        """
        pass

    def moss_type(self) -> Type:
        """
        :return: MOSS as default
        """
        module = self.module()
        if "MOSS" in module.__dict__:
            t = module.__dict__["MOSS"]
            if not inspect.isclass(t):
                raise TypeError(f"defined MOSS type {t} is not a class")
        return MOSS

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

    def execute(
            self,
            *,
            code: str,
            target: str,
            args: Optional[List[str]] = None,
            kwargs: Optional[Dict[str, str]] = None,
    ) -> "MOSSResult":
        """
        基于 moos 提供的上下文, 运行一段代码.
        :param code: 需要运行的代码.
        :param target: 指定上下文中一个变量名用来获取返回值. 如果为空, 则返回 None. 如果是一个方法, 则会运行它.
        :param args: 如果 args 不为 None, 则认为 target 是一个函数, 并从 locals 里指定参数
        :param kwargs: 类似 args
        :return: 根据 result_name 从 code 中获取返回值.
        :exception: any exception will be raised, handle them outside
        """
        compiled = self.module()
        with self.runtime_ctx():
            # 使用 module 自定义的 exec
            if MOSS_EXEC_EVENT in compiled.__dict__:
                fn = compiled.__dict__[MOSS_EXEC_EVENT]
                return fn(self, code, target, args, kwargs)
            # 使用系统默认的 exec
            from ghostiss.moss2.lifecycle import __moss_exec__
            return __moss_exec__(self, code, target, args, kwargs)

    def destroy(self) -> None:
        """
        方便垃圾回收.
        """
        pass


class MOSSResult(NamedTuple):
    """
    result of the moss runtime execution.
    """
    returns: Any
    std_output: str
    pycontext: PyContext
