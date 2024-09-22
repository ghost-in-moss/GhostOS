from os.path import dirname, join
from ghostos.prototypes.ghostfunc.decorator import GhostFunc
from ghostos.prototypes.ghostfunc.prepare import init_ghost_func_container

"""
this is a toy that using MOSS to implement a light-weight dynamic function based by llm code generation.
"""

__all__ = ['ghost_func', 'GhostFunc', 'init_ghost_func_container', 'init_ghost_func']

demo_dir = join(dirname(dirname(dirname(__file__))), 'demo')
_container = init_ghost_func_container(demo_dir)

ghost_func = GhostFunc(_container)


def init_ghost_func(
        root_dir: str,
        configs_path: str = "configs",
        llm_conf_path: str = "llms_conf.yml",
) -> GhostFunc:
    """
    init ghost func instance from a dir keeping configs.
    :param root_dir: root dir of runtime and configs.
    :param configs_path: configs dir path from root dir
    :param llm_conf_path: llm config path in configs dir
    :return: instance of GhostFunc, with decorators.
    """
    ghost_func_container = init_ghost_func_container(root_dir, configs_path, llm_conf_path)
    return GhostFunc(ghost_func_container)
