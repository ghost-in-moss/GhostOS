from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional, List, Dict, Any
    from ghostiss.moss2.prompts import AttrPrompts
    from ghostiss.moss2.abc import MOSSPrompter, MOSSResult, MOSSExecutor

"""
这个文件提供了 MOSS 生命周期的关键方法, 每一个都是可选的.
这样一个 Module 要在 MOSS 中运行时, 如果定义了这些方法或类, 就会替换掉默认生命周期里的相关方法. 
"""


class MOSS(ABC):
    """
    可以在代码里自定一个名为 MOSS 的类.
    如果定义了, 或者引用了, 会自动生成它的实例.
    会对类上定义的属性进行依赖注入.
    对类上定义的方法名也按名称进行依赖注入. 没有注入对象时保留原方法.
    这个类不要有 init 方法.
    它的源码就是 MOSS 的 Prompt.
    如果给 MOSS 注入了它未定义的属性或方法, 也会追加到它生成的 Prompt 里.
    """
    pass


def __moss_compiled__(runtime: "MOSSPrompter") -> "MOSSPrompter":
    """
    从 compile 中获取 MOSSRuntime, 并对它进行初始化.
    可选的魔术方法. 如果定义的话, MOSS 执行 compile 的阶段会默认执行它.

    主要解决各种注入方面的需求:
    runtime.inject()
    runtime.register()
    """
    return runtime


def __prompt__() -> str:
    """
    可选的魔术方法.
    使用这个方法, 可以完全自定义当前文件生成的 prompt.
    系统不做任何干预.
    """
    pass


def __attr_prompts__() -> "AttrPrompts":
    """
    生成本地变量生成的 prompt.
    可选的魔术方法.

    系统本身会反射代码通过 import 获得的本地变量 (这些变量 __module__ 和本地 __name__ 不同),
    为它们中的一部分添加 prompt. 通常有这么几种会生成:
    - builtin 的对象: 不做任何展示.
    - 拥有 `__prompt__: str` 属性的 class/function/module.
    - 拥有 `__attr_prompts__(self): Dict` 方法的类. 会按默认的规则进行拼装.
    - 类: 默认不展示.
      - is_abstract 类: 只展示源码.
      - 继承自 BaseModel 类或者 typing: 展示源码.
    - 方法: 默认只展示 func def + doc
    - typing 类型, 比如 Union 等.
    - 如果引用对象所在的模块本身包含 __attr_prompts__(), 则会递归使用它的 prompt.

    而这个方法则可以替代或追加必要的 prompt, 与系统生成的合并.
    还有一些在 <moss></moss> 标记内定义的代码, 想要在 prompt 里呈现, 也需要在这个方法里定义.

    :returns: name => prompt. if prompt is tuple, it contains two elements: Tuple[prompt: str, assignment: bool].

    如果一个 name 对应的 attr 是一个 class 或者 function/method, assignment 默认为 false.

    推荐使用 ghostiss.moss.prompts 模块下提供的各种反射方法.
    """
    return []


def __moss_prompt__(prompter: "MOSSPrompter") -> str:
    """
    使用 MOSS Runtime 生成 prompt 的方法.
    可选的魔术方法. 定义的话, runtime.moss_context_prompt 实际上会使用这个方法.

    这个方法生成的 Prompt, 会用来描述当前文件, 其中包含了注入的 MOSS 类和 moss 实例.
    """
    from ghostiss.moss2.utils import escape_string_quotes
    # 获取原始的代码.
    origin_code = prompter.pycontext_code(model_visible=True)
    # 基于 origin code 生成关于这些变量的 prompt.
    escaped_code_prompt = prompter.pycontext_code_prompt()
    # 这部分变量的描述, 放到一个 string 里表示不污染当前上下文.
    escaped_code_prompt = escape_string_quotes(escaped_code_prompt, '"""')
    code_prompt_part = ""
    if escaped_code_prompt:
        code_prompt_part = f'''
"""
# information about values above:
{escaped_code_prompt}
"""
'''
    # 获取关于 MOSS 的 prompt.
    moss_prompt = prompter.moss_prompt()

    # 生成完整的 prompt.
    prompt = f"""
{origin_code}
\"""
# 
{code_prompt_part}
\"""

# Notice: type, method and values defined in the code above are immutable in multi-turns chat or thought.
# You are equipped with a MOSS interface below, which can inject module or define attributes in multi-turns.

{moss_prompt}
"""

    return prompt


def __moss_exec__(
        executor: "MOSSExecutor",
        code: str,
        target: str,
        args: "Optional[List[str]]" = None,
        kwargs: "Optional[Dict[str, Any]]" = None,
) -> "MOSSResult":
    """
    基于 MOSS Runtime 执行一段代码, 并且调用目标方法或返回目标值.
    :param executor: moss runtime
    :param code: 会通过 execute
    :param target: 指定一个上下文中的变量, 如果是 callable 则执行它, 如果不是 callable 则直接返回.
    :param args: 为 target 准备的 *args 参数, 这里只需要指定上下文中的变量名.
    :param kwargs: 为 target 准备的 **kwargs 参数, 这里需要指定 argument_name => module_attr_name
    """
    from RestrictedPython import safe_builtins
    from typing import Callable
    from ghostiss.moss2.abc import MOSSResult, MOSS
    module = executor.module()
    module.__dict__["moss"] = executor.moss()
    # 展示的 MOSS prompt 和真实的 moss 不一样.
    module.__dict__["MOSS"] = MOSS
    module.__dict__["__builtins__"] = safe_builtins
    # 注意使用 runtime.exec_ctx 包裹有副作用的调用.
    with executor.runtime_ctx():
        compiled = compile(code, filename='<MOSS>', mode='exec')
        exec(compiled, module.__dict__)

    if target not in module.__dict__:
        raise NotImplementedError(f"target `{target}` not implemented")

    target_module_attr = module.__dict__[target]
    is_function = isinstance(target_module_attr, Callable)
    if args is not None or kwargs is not None and not is_function:
        raise TypeError(f"target {target} is not callable")

    if is_function:
        real_args = []
        real_kwargs = {}
        if args:
            for attr_name in args:
                if attr_name not in module.__dict__:
                    raise AttributeError(f"module has no attribute `{attr_name}` for `{target}`")
                arg_val = getattr(module, attr_name, None)
                real_args.append(arg_val)
        if kwargs:
            for argument_name, attr_name in kwargs.items():
                if attr_name not in module.__dict__:
                    raise AttributeError(f"module has no attribute {attr_name} for `{target}`")
                real_kwargs[argument_name] = getattr(module, attr_name, None)
        # 注意使用 runtime.exec_ctx 包裹有副作用的调用.
        with executor.runtime_ctx():
            returns = target_module_attr(*real_args, **real_kwargs)
    else:
        returns = target_module_attr
    std_output = executor.dump_std_output()
    pycontext = executor.dump_context()
    return MOSSResult(returns, std_output, pycontext)
