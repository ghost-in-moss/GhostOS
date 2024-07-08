from RestrictedPython import safe_globals
from typing import Any, Dict, Optional, TypedDict, List


def execute(code: str, **kwargs) -> Any:
    """
    基于给定的上下文, 运行一段新增的代码.
    """
    locals__ = kwargs
    locals__["result__"] = None
    compiled = compile(code, "temporary_exec", 'exec')
    # todo: 检查 import 进行禁止, 或者修改 __import__
    exec(compiled, locals__, None)
    return locals__["result__"]
