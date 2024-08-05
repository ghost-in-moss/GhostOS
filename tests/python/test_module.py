from types import ModuleType


def test_module_attr_with_module():
    module = ModuleType('test_module')
    code = """
class Foo:
    foo: int = 1
    
f = Foo() 
a = 123
"""
    exec(code, module.__dict__)
    assert module.__name__ == 'test_module'
    Foo = module.__dict__['Foo']
    assert Foo.__module__ == 'test_module'
    f = module.__dict__['f']
    assert f.__module__ == 'test_module'
    a = module.__dict__['a']
    assert not hasattr(a, '__module__')


