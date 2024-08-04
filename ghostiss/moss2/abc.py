from typing import Dict, Any, Union, List, Optional, NamedTuple, Type, Tuple
from types import ModuleType
from abc import ABC, abstractmethod
from ghostiss.container import Container
from ghostiss.moss2.pycontext import PyContext, SerializableType
from ghostiss.moss2.prompts import Prompter

"""
MOSS 是 Model-oriented Operating System Simulation 的简写. 
它将系统当前上下文的 API 通过全代码的方式 Prompt 给模型, 让模型直接生成代码并且执行. 

MOSS 通过 PyContext 来定义一个可持久化, 可以复原的上下文. 
可以在多轮对话, 或者多轮思考中, 反复还原这个上下文. 

使用 moss 的完整生命周期的伪代码如下 (系统会自动集成)

# 第一步, 获取 MOSSCompiler 对象. 
compiler: MOSSCompiler = container.force_fetch(MOSSCompiler)

# 第二步, compiler 可以 inject 其它类库, 或 join pycontext, 然后 compile
runtime: MOSSRuntime = compiler.compile(xxx)

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
    'MOSS', 'MetaMOSS',
    'MOSSCompiler', 'MOSSResult', 'MOSSRuntime',
]


class MOSS(ABC):
    """
    Language Model-oriented Operating System Simulation.
    Full python code interface for large language models in multi-turns chat or thinking.
    """

    @abstractmethod
    def define(
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
            from module.submodule import module_attr_name as var
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


class MetaMOSS(MOSS):
    """
    可以修改当前代码的 MOSS.
    """

    @abstractmethod
    def append_code(self, code: str) -> None:
        pass


class MOSSCompiler(ABC):
    """
    language Model-oriented Operating System Simulation
    full python code interface for large language models
    """

    # --- 创建 MOSS 的方法 --- #
    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    def pycontext(self) -> PyContext:
        pass

    @abstractmethod
    def join_context(self, context: PyContext) -> "MOSSCompiler":
        """
        为 MOSS 上下文添加一个可以持久化存储的 context 变量.
        :param context:
        :return:
        """
        pass

    def compile(self, meta_mode: bool = False) -> "MOSSRuntime":
        runtime = self._compile(meta_mode)
        compiled = runtime.compiled()
        optional_runtime_prepare_fn = "__moss_compile__"
        if optional_runtime_prepare_fn in compiled.__dict__:
            fn = compiled.__dict__[optional_runtime_prepare_fn]
            return fn(runtime)
        return runtime

    @abstractmethod
    def _compile(self, meta_mode: bool = False) -> "MOSSRuntime":
        pass


class MOSSRuntime(ABC):

    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    def injects(self, **attrs: Union[Any, Prompter]) -> "MOSSCompiler":
        pass

    @abstractmethod
    def predefined_code(self, model_visible: bool = True) -> str:
        pass

    @abstractmethod
    def predefined_code_prompt(self) -> str:
        pass

    @abstractmethod
    def moss(self) -> MOSS:
        pass

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
        compiled = self.compiled()
        if "__moss__prompt__" in compiled.__dict__:
            fn = compiled.__dict__["__moss__prompt__"]
            return fn(self)
        from ghostiss.moss2.lifecycle import __moss_prompt__
        return __moss_prompt__(self)

    @abstractmethod
    def compiled(self) -> ModuleType:
        pass

    @abstractmethod
    def locals(self) -> Dict[str, Any]:
        """
        返回 moss 运行时的上下文变量, 可以结合 exec 提供 locals 并且运行.
        """
        pass

    @abstractmethod
    def dump_context(self) -> PyContext:
        """
        返回当前的可存储上下文.
        """
        pass

    @abstractmethod
    def dump_std_output(self) -> str:
        """
        std output in
        :return: str
        """
        pass

    @abstractmethod
    def exec_ctx(self):
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
        compiled = self.compiled()
        execute_lifecycle_fn_name = "__moss_execute__"
        if execute_lifecycle_fn_name in compiled.__dict__:
            fn = compiled.__dict__[execute_lifecycle_fn_name]
            return fn(self, code, target, args, kwargs)
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
