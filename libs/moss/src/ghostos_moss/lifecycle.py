from typing import TYPE_CHECKING
from typing import Optional, List, Dict, Any

if TYPE_CHECKING:
    from ghostos_moss.prompts import AttrPrompts
    from ghostos_moss.abcd import MossPrompter, Execution, MossRuntime, MossCompiler, Moss

"""
这个文件提供了 MOSS 生命周期的关键方法, 每一个都是可选的.
这样一个 Module 要在 MOSS 中运行时, 如果定义了这些方法或类, 就会替换掉默认生命周期里的相关方法. 
"""

__all__ = [
    '__moss_compile__',  # prepare moss compiler, handle dependencies register
    '__moss_compiled__',  # when moss instance is compiled
    '__moss_attr_prompts__',  # generate custom local attr prompt
    '__moss_module_prompt__',  # define module prompt
    '__moss_exec__',  # execute the generated code attach to the module
]

# todo: 整体重命名一遍魔术方法. 魔术方法并不是一个比较好的实现, 太依赖用户的知识了.


def __moss_compile__(compiler: "MossCompiler") -> "MossCompiler":
    """
    从 compile 中获取 MOSSRuntime, 并对它进行初始化.
    可选的魔术方法. 如果定义的话, MOSS 执行 compile 的阶段会默认执行它.

    主要解决各种注入方面的需求:
    compiler.inject()
    compiler.register()
    """
    return compiler


def __moss_compiled__(moss: "Moss") -> None:
    """
    当 Moss 对象被编译完成时, 回调的 hook
    :param moss:
    :return:
    """
    return


def __moss_attr_prompts__() -> "AttrPrompts":
    """
    生成本地变量生成的 prompt.
    可选的魔术方法.

    系统本身会反射代码的本地变量, 为它们中的一部分添加 prompt.
    默认的反射方法见 ghostos.moss.prompts.prompts.py 文件.

    而这个方法则可以替代或追加必要的 prompt, 优先于系统生成的反射.
    还有一些在 <moss-hide></moss-hide> 标记内定义的代码, 想要在 prompt 里呈现, 也可以在这个方法里定义.

    推荐使用 ghostos.moss.prompts 模块下提供的各种反射方法.
    :returns: Iterable[Tuple[name, prompt]] . 其中 name 只是为了去重.
    """
    return []


def __moss_module_prompt__(prompter: "MossPrompter", attr_prompts: Optional[Dict[str, str]] = None) -> str:
    """
    使用 MOSS Runtime 生成 prompt 的方法.
    可选的魔术方法. 定义的话, runtime.moss_context_prompt 实际上会使用这个方法.

    这个方法生成的 Prompt, 会用来描述当前文件, 其中包含了注入的 MOSS 类和 moss 实例.
    """
    from ghostos_moss.utils import escape_string_quotes

    # 获取原始的代码.
    origin_code = prompter.get_source_code(exclude_hide_code=True)

    # 基于 origin code 生成关于这些变量的 prompt.
    attrs_prompt_str = prompter.dump_imported_prompt(attr_prompts=attr_prompts)
    code_prompt_part = ""
    if attrs_prompt_str:
        # 这部分变量的描述, 放到一个 string 里表示不污染当前上下文.
        attrs_prompt_str = escape_string_quotes(attrs_prompt_str, '"""')
        code_prompt_part = f'''

# more details about some module attrs above, are list below (quoted by <attr></attr>):
"""
{attrs_prompt_str}
"""
'''

    # 生成完整的 prompt. 预计 MOSS 的描述已经在上下文里了.
    prompt = f"""
{origin_code}
{code_prompt_part}
"""

    return prompt


def __moss_exec__(
        runtime: "MossRuntime",
        *,
        target: str,
        code: "Optional[str]" = None,
        local_args: "Optional[List[str]]" = None,
        local_kwargs: "Optional[Dict[str, Any]]" = None,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
) -> "Execution":
    """
    基于 MOSS Runtime 执行一段代码, 并且调用目标方法或返回目标值.
    :param runtime: moss runtime
    :param code: 会通过 execute
    :param target: 指定一个上下文中的变量, 如果是 callable 则执行它, 如果不是 callable 则直接返回.
    :param local_args: 为 target 准备的 *args 参数, 这里只需要指定上下文中的变量名.
    :param local_kwargs: 为 target 准备的 **kwargs 参数, 这里需要指定 argument_name => module_attr_name
    :param args: 从外部注入的参数变量
    :param kwargs: 从外部注入的参数变量.
    """
    from typing import Callable
    from ghostos_moss.abcd import Execution
    pycontext = runtime.dump_pycontext()
    pycontext.execute_code = code
    pycontext.executed = False

    local_values = runtime.locals()
    # 注意使用 runtime.exec_ctx 包裹有副作用的调用.
    if code:
        filename = pycontext.module if pycontext.module is not None else "<MOSS>"
        compiled = compile(code, filename=filename, mode='exec')
        exec(compiled, local_values)

    if target not in local_values:
        raise NotImplementedError(f"target `{target}` not implemented")

    target_module_attr = local_values.get(target, None)

    # 如果定义了参数, 就必须是 callable 方法.
    has_args = local_args is not None or local_kwargs is not None or args is not None or kwargs is not None
    if isinstance(target_module_attr, Callable):
        real_args = []
        real_kwargs = {}
        if local_args:
            for attr_name in local_args:
                if attr_name not in local_values:
                    raise AttributeError(f"module has no attribute `{attr_name}` for `{target}`")
                arg_val = local_values.get(attr_name, None)
                real_args.append(arg_val)
        if args:
            real_args.extend(args)
        if local_kwargs:
            for argument_name, attr_name in local_kwargs.items():
                if attr_name not in local_values:
                    raise AttributeError(f"module has no attribute {attr_name} for `{target}`")
                real_kwargs[argument_name] = local_values.get(attr_name, None)
        if kwargs:
            real_kwargs.update(kwargs)
        # 注意使用 runtime.exec_ctx 包裹有副作用的调用.
        with runtime.redirect_stdout():
            returns = target_module_attr(*real_args, **real_kwargs)
    elif has_args:
        raise TypeError(f"target '{target}' value '{target_module_attr}' is not callable")
    else:
        returns = target_module_attr
    std_output = runtime.dump_std_output()
    pycontext = runtime.dump_pycontext()
    pycontext.executed = True
    return Execution(returns, std_output, pycontext)
