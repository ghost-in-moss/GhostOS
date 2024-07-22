from types import ModuleType


def test_module_attr_with_module():
    module = ModuleType('test_module')
    code = """
class Foo:
    foo: int = 1
"""
    exec(code, module.__dict__)
    assert module.__name__ == 'test_module'
    f = module.__dict__['Foo']
    assert f.__module__ == 'test_module'
