import inspect
from types import ModuleType
from typing import get_type_hints


def test_module_attr_with_module():
    module = ModuleType('test_module')
    code = """
import inspect
from inspect import getsource
class Bar:
    bar: int = 123
class Foo:
    '''test'''
    foo: int = 1
    bar: Bar
    
f = Foo() 
a = 123
"""
    exec(code, module.__dict__)
    assert module.__name__ == 'test_module'
    Foo = module.__dict__['Foo']
    assert Foo.__module__ == 'test_module'
    assert Foo.__doc__ == 'test'
    f = module.__dict__['f']
    assert f.__module__ == 'test_module'
    a = module.__dict__['a']
    assert not hasattr(a, '__module__')
    typehints = get_type_hints(Foo)
    assert "foo" in typehints
    assert typehints["foo"] is int
    assert "bar" in typehints

    assert "inspect" in module.__dict__
    i = module.__dict__['inspect']
    assert inspect.ismodule(i)
    assert i.__name__ == 'inspect'

    getsource = module.__dict__['getsource']
    assert getsource.__module__ == 'inspect'


