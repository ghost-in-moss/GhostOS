from RestrictedPython import compile_restricted, safe_globals


def test_restrictedpython_import():
    code = """
import sympy 
import inspect
source = inspect.getsource(sympy)
"""
    compiled = compile_restricted(code, filename="<test>", mode='exec')
    e = None
    try:
        exec(compiled, safe_globals)
    except ImportError as err:
        e = err
    assert e is not None
