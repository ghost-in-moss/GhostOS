from ghostos.prototypes.aifunc.app import run_aifunc
from ghostos.core.aifunc import AIFunc, AIFuncResult
from os.path import dirname

__all__ = ["run_aifunc", "quick_run_aifunc"]


def quick_run_aifunc(
        aifunc: AIFunc,
        current_path: str,
        dirname_times: int = 0,
        debug: bool = True,
) -> AIFuncResult:
    """
    create aifunc runtime with default paths and run it
    """
    root_dir = current_path
    for i in range(dirname_times):
        root_dir = dirname(root_dir)
    return run_aifunc(root_dir, aifunc, debug=debug)
