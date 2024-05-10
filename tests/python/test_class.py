def test_class_name():
    class Foo:
        pass

    assert Foo.__name__ == 'Foo'


class Bar:
    pass


def test_module_name():
    # pytest 运行路径决定了 module 的路径.
    assert Bar.__module__ != 'tests.python.test_class'
    assert Bar.__module__ == 'test_class'


def test_runtime_path():
    from runpy import run_path
