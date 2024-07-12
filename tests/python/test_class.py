from typing import Dict, SupportsAbs as _SupportsAbs
import inspect


def test_class_name():
    class Foo:
        pass

    assert Foo.__name__ == 'Foo'


class Bar:
    bar = "test"
    """PEP258"""

    @staticmethod
    def static() -> str:
        return "test"


def test_module_name():
    # pytest 运行路径决定了 module 的路径.
    assert Bar.__module__ != 'tests.python.test_class'
    assert Bar.__module__ == 'test_class'


def test_class_dict_attrs():
    class Foo:
        def __init__(self, doc: str, values: Dict[str, str]):
            self.__doc__ = doc
            self.__dict__.update(values)

    f = Foo("test", {"a": "b", "c": "d"})
    assert inspect.getdoc(f) == "test"
    assert f.a == "b"
    assert f.c == "d"


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


def test_redefine_class_method():
    class Foo:
        foo: int = 10

        def fn(self) -> int:
            return self.foo

    class Zoo:
        foo: int = 5

        def fn(self) -> int:
            return self.foo

    f = Foo()
    z = Zoo()
    setattr(f, "fn", z.fn)
    assert f.fn() == 5


def test_get_static_method_source():
    source = inspect.getsource(Bar.static)
    assert source.lstrip().startswith("@staticmethod")


def test_method_doc_indent():
    class Foo:
        def bar(self):
            """
            :return:
            """
            return ""

    doc = inspect.getdoc(Foo.bar)
    # 前缀会自动被干掉.
    assert not doc.startswith("   ")


def test_method_has_name_ma():
    assert hasattr(Bar.static, "__name__")
    assert Bar.static.__name__ == "static"
    assert Bar.static.__class__.__name__ == "function"


def test_method_set_attr():
    class Foo:
        foo: int = 10

    f = Foo()
    setattr(f, "foo", 20)
    assert f.foo == 20
    setattr(f, 'foo', 'foo')
    # 可以变更属性的类型.
    assert f.foo == "foo"


def test_type_qualname():
    assert _SupportsAbs.__qualname__ == "SupportsAbs"
    assert Bar.__qualname__ == "Bar"


def test_get_members():
    class Foo:

        def foo(self) -> int:
            return 123

        @staticmethod
        def bar(self) -> int:
            return 456

    # 类里取不到 staticmethod
    assert len(list(inspect.getmembers(Foo(), inspect.ismethod))) == 1
    # 类里取不到 method
    assert len(list(inspect.getmembers(Foo, inspect.ismethod))) == 0


def test_instance_doc():
    class Foo:
        """
        test
        """
        pass

    f = Foo()
    assert f.__doc__.strip() == "test"
    f.__doc__ = "hello"
    # 不会污染父类.
    assert f.__doc__ == "hello"
    assert Foo.__doc__.strip() == "test"
