from os.path import dirname
from ghostos.prototypes.console import ConsoleApp
from ghostos.prototypes.ghostfunc import GhostFunc, init_ghost_func_container
from ghostos.core.moss import moss_test_suite
from ghostos.prototypes.mosstemp import init_moss_module

__all__ = ['console_app', 'ghost_func', 'init_moss_module', 'moss_test_suite']

new_moss_test_suite = moss_test_suite
""" useful to run moss file test cases."""

init_moss_template = init_moss_module
"""initialize moss template content to a target module"""

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
