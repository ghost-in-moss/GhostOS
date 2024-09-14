from os.path import dirname
from ghostos.prototypes.console import ConsoleApp

__all__ = ['console_app']

root_dir = dirname(dirname(__file__))

console_app = ConsoleApp(root_dir)
""" 
openbox console app that run agent in commmand line console.
see:
console_app.run_thought(...)
console_app.run_console(...)
"""
