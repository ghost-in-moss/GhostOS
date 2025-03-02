from typing import Dict, SupportsAbs as _SupportsAbs, List
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


def test_setattr_to_parent_class():
    class Foo:
        foo: int = 10

    class Zoo(Foo):
        Zoo: str = "test"

    z = Zoo()
    setattr(Foo, "bar", 20)
    assert z.bar == 20
    assert Zoo.bar == 20


def test_setattr_with_func():
    def hello() -> str:
        return "world"

    class Foo:
        foo: int = 10

    setattr(Foo, "hello", hello)
    assert Foo.hello() == "world"


def test_subclass():
    # self is self's subclass. humor but reasonable
    assert issubclass(Bar, Bar)


def test_method_belongs_to_class():
    class Foo:
        def foo(self):
            return 1

    class Bar(Foo):
        pass

    assert Bar.foo.__module__ == Foo.__module__
    assert Bar.foo.__qualname__.startswith(Foo.__qualname__)


def test_subclass_is_parent():
    class Foo:
        foo: int = 10

    class Foo1(Foo):
        foo: int = 11

    assert Foo1 is not Foo


def test_generic_class_is_same():
    from typing import Generic, TypeVar
    T = TypeVar("T")

    class Foo(Generic[T]):
        def __init__(self, val: T):
            self.val = val

    assert Foo[int] is Foo[int]
    obj1 = Foo[int](1)
    obj2 = Foo[int](2)
    assert type(obj1) is type(obj2)


def test_protocol_and_abc():
    from abc import ABC
    from typing import Protocol

    class _Foo(Protocol):
        foo = 1

    class _Bar(_Foo, ABC):
        pass

    class _Baz(_Bar):
        pass

    b = _Baz()
    assert b.foo == 1


def test_attr_of_class():
    class Foo:
        foo = 1
        bar: int
        baz: int = 3

    assert Foo.foo == 1
    assert Foo().foo == 1
    assert not hasattr(Foo, "bar")
    assert not hasattr(Foo(), "bar")
    from typing import get_type_hints
    props = get_type_hints(Foo)
    assert "bar" in props
    assert "baz" in props
    assert hasattr(Foo, "baz")
    assert hasattr(Foo(), "baz")


def test_class_var_list():
    class Foo:
        foo: List[str] = []

        def __init__(self, val: List[str]):
            self.foo = val

    f = Foo(["a", "b"])
    assert f.foo == ["a", "b"]
    assert Foo.foo == []
    f2 = Foo([])
    assert f.foo == ["a", "b"]
    assert f2.foo == []

    class Bar:
        bar: List[str] = []

        def __init__(self, val: List[str]):
            self.bar.extend(val)

    b = Bar(["a", "b"])
    assert b.bar == ["a", "b"]
    # be updated
    assert Bar.bar == ["a", "b"]


def test_class_eval():
    class Foo:
        def __init__(self, code: str):
            self.code = code
            self.foo = 1

        def run(self):
            code = "\n".join([line.lstrip() for line in self.code.splitlines()])
            exec(code)

    f = Foo(
        "print(self)\n"
        "print(self.foo)\n"
        "self.foo = 2\n"
    )
    f.run()
    assert f.foo == 2
