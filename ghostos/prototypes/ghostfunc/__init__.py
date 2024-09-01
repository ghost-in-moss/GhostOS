from os.path import dirname, join
from ghostos.prototypes.ghostfunc.decorator import GhostFunc
from ghostos.prototypes.ghostfunc.prepare import init_ghost_func_container

"""
this is a toy that using MOSS to implement a light-weight dynamic function based by llm code generation.
"""

__all__ = ['ghost_func']


def _demo_path() -> str:
    root_path = dirname(dirname(dirname(dirname(__file__))))
    return join(root_path, 'demo/ghostos')


_container = init_ghost_func_container(root_path=_demo_path())

ghost_func = GhostFunc(_container)
