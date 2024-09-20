from os.path import dirname
from ghostos.prototypes.console import ConsoleApp
from ghostos.prototypes.ghostfunc import GhostFunc, init_ghost_func_container

from ghostos.prototypes.mosstemp import init_moss_module
"""initialize moss template content to a target module"""

__all__ = ['console_app', 'ghost_func', 'init_moss_module']

root_dir = dirname(__file__)

console_app = ConsoleApp(root_dir)
""" 
openbox console app that run agent in command line console.
see:
console_app.run_thought(...)
console_app.run_console(...)
"""

_ghost_func_container = init_ghost_func_container(root_dir)

ghost_func = GhostFunc(_ghost_func_container)
"""
ghost_func provide decorators that wrap a function to a ghost func, which produce code in runtime.
ghost_func is a toy born during early development test case.
"""
