from abc import abstractmethod
from typing import Union, Type, Protocol, TypedDict, NamedTuple
import inspect


def test_get_source():
    """
    test inspect getsource with doc and codes
    """
    # data is str; comment is part of the codes.
    data = inspect.getsource(test_get_source)
    assert "inspect.getsource" in data and "assert" in data
    assert "test" in data
    assert "# data is str" in data


def test_get_source_from_obj():
    fn = test_get_source
    data = inspect.getsource(fn)
    assert "test" in data


def test_class_object_source():
    class Test:
        foo: str

    t = Test()
    e = None
    try:
        # can not get source from instance
        data = inspect.getsource(t)
        assert "class Test" in data
    except TypeError as exp:
        e = exp
    finally:
        assert e is not None


def test_inspect_type_checkers():
    class Foo:
        foo: int

    f = Foo()
    assert isinstance(f, Foo)
    assert inspect.isclass(Foo)
    assert inspect.isclass(type(f))
    assert not inspect.isclass(None)
    assert not inspect.isbuiltin(None)
    assert not inspect.isbuiltin(f)
    assert not inspect.isfunction(f)


def test_get_doc():
    a = 123
    """test"""

    try:
        doc = inspect.getdoc(a)
    except Exception as e:
        assert e is not None

    b = "123"
    """test"""

    # 不是想要的类型.
    doc = inspect.getdoc(b)
    assert doc is not None


def test_var_module():
    a = 123
    assert not hasattr(a, "__module__")

    class Foo:
        foo: int

    assert hasattr(Foo, "__module__")
    assert Foo.__module__ == "test_inspect"


def test_is_builtin():
    a = 123
    # is builtin 只可以用来判断函数.
    assert not inspect.isbuiltin(a)
    assert not inspect.isbuiltin(int)
    assert not inspect.isbuiltin(Union)
    assert inspect.isbuiltin(print)
    assert not inspect.isbuiltin(dict)
    assert not inspect.isbuiltin(set)

    # 判断类的方法不一样.
    int_module = inspect.getmodule(int)
    assert int_module.__name__ == "builtins"


def test_get_method_source():
    class Foo:

        def foo(self) -> str:
            return "foo"

        @abstractmethod
        def abc(self) -> str:
            pass

        @classmethod
        def kls(cls) -> str:
            pass

        @staticmethod
        def static() -> str:
            return "foo"

    f = Foo()
    assert inspect.ismethod(f.foo)
    assert not inspect.isfunction(f.foo)
    assert not inspect.isabstract(f.foo)
    # abstract 只针对类.
    assert not inspect.isabstract(f.abc)
    assert inspect.ismethod(f.kls)
    assert isinstance(Foo, type)
    assert isinstance(int, type)
    # 静态方法本质就是 function.
    assert inspect.isfunction(f.static)
    assert not inspect.ismethod(f.static)


def test_is_class():
    assert not inspect.isclass(123)
    assert not inspect.isclass("123")
    assert not inspect.isclass({})
    assert not inspect.isclass(())
    assert not inspect.isclass(set())
    # 不用这么麻烦, 看看方法的实现就知道了....

    from abc import ABC
    class Cool(ABC):
        bar: int = 123

    assert inspect.isclass(Cool)


def test_getsource():
    class Parent:
        foo: int = 123

    class Child(Parent):
        bar: int = 456

    source = inspect.getsource(Child)
    assert "foo" not in source


class SomeClass:
    foo: int = 123

    __add_info: str = ""


class SubClass(SomeClass):
    bar: int = 456


SubClass.__add_info = "test"


def test_getsource_without_added_code():
    code = inspect.getsource(SubClass)
    assert "__add_info" not in code


def test_get_signature():
    value = inspect.signature(SomeClass)
    assert value is not None


def test_get_source_from_union():
    a = Union[int, str]
    e = None
    try:
        data = inspect.getsource(a)
    except TypeError as exp:
        e = exp
    assert e is not None


def test_get_source_from_protocol():
    class Foo(Protocol):
        a: int

    source = inspect.getsource(Foo)
    assert len(source) > 0


def test_get_source_from_typed_dict():
    class Foo(TypedDict):
        a: int

    source = inspect.getsource(Foo)
    assert len(source) > 0


def test_get_source_from_named_tuple():
    class Foo(NamedTuple):
        a: int

    source = inspect.getsource(Foo)
    assert len(source) > 0
    assert inspect.isclass(Foo)


def test_get_source_from_method():
    class Foo:
        def method(self, a: int) -> int:
            return a

    source = inspect.getsource(Foo.method)
    assert len(source) > 0
    assert not inspect.ismethod(Foo.method)
    assert inspect.isfunction(Foo.method)
