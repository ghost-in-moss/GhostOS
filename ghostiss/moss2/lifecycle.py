from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional, List, Dict, Any
    from ghostiss.moss2.abc import MOSSRuntime, MOSSResult


def __moss_compile__(compiled: "MOSSRuntime") -> "MOSSRuntime":
    """
    从 compile 中获取 MOSSRuntime, 并对它进行初始化.
    可选的魔术方法. 如果定义的话, MOSS 执行 compile 的阶段会默认执行它.

    可以在这个方法里人工向 MOSS 注入一些预设的类型.
    比如 compiled.inject(**vars)
    """
    return compiled


def __moss_prompt__(runtime: "MOSSRuntime") -> str:
    """
    使用 MOSS Runtime 生成 prompt 的方法.
    可选的魔术方法. 定义的话, runtime.moss_context_prompt 实际上会使用这个方法.

    这个方法生成的 Prompt, 会用来描述当前文件, 其中包含了注入的 MOSS 类和 moss 实例.
    """
    from ghostiss.moss2.utils import parse_doc_string_with_quotes
    origin_code = runtime.predefined_code(model_visible=True)
    code_prompt = runtime.predefined_code_prompt()
    code_prompt = parse_doc_string_with_quotes(code_prompt, '"""')
    code_prompt_part = ""
    if code_prompt:
        code_prompt_part = f'''
"""
# information about values above:
{code_prompt}
"""
'''
    moss_prompt = runtime.moss_prompt()
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
        runtime: "MOSSRuntime",
        code: str,
        target: str,
        args: "Optional[List[str]]" = None,
        kwargs: "Optional[Dict[str, Any]]" = None,
) -> "MOSSResult":
    """
    基于 MOSS Runtime 执行一段代码, 并且调用目标方法或返回目标值.
    :param runtime: moss runtime
    :param code: 会通过 execute
    :param target: 指定一个上下文中的变量, 如果是 callable 则执行它, 如果不是 callable 则直接返回.
    :param args: 为 target 准备的 *args 参数, 这里只需要指定上下文中的变量名.
    :param kwargs: 为 target 准备的 **kwargs 参数, 这里需要指定 argument_name => module_attr_name
    """
    from RestrictedPython import safe_builtins
    from typing import Callable
    from ghostiss.moss2.abc import MOSSResult, MOSS
    module = runtime.compiled()
    module.__dict__["moss"] = runtime.moss()
    # 展示的 MOSS prompt 和真实的 moss 不一样.
    module.__dict__["MOSS"] = MOSS
    module.__dict__["__builtins__"] = safe_builtins
    # 注意使用 runtime.exec_ctx 包裹有副作用的调用.
    with runtime.exec_ctx():
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
        with runtime.exec_ctx():
            returns = target_module_attr(*real_args, **real_kwargs)
    else:
        returns = target_module_attr
    std_output = runtime.dump_std_output()
    pycontext = runtime.dump_context()
    return MOSSResult(returns, std_output, pycontext)
