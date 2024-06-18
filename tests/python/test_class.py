def test_class_name():
    class Foo:
        pass

    assert Foo.__name__ == 'Foo'


class Bar:
    bar = "test"
    """PEP258"""


def test_module_name():
    # pytest 运行路径决定了 module 的路径.
    assert Bar.__module__ != 'tests.python.test_class'
    assert Bar.__module__ == 'test_class'


def test_class_attr_docstring():
    assert Bar.bar == 'test'
    # 暂时没发现如何获取属性的注释.
    # print(Bar.bar.__doc__)


def test_extends_with_property():
    from abc import ABC, abstractmethod

    class Foo(ABC):
        @property
        @abstractmethod
        def foo(self) -> str:
            pass

    class Foo2(Foo):

        @property
        def foo(self) -> str:
            return "bar"

    bar = Foo2()
    assert bar.foo == "bar"
