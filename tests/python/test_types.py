from typing import Union, TypedDict, Optional
import inspect


def test_str_2_num():
    a = "123"
    assert a != 123
    assert int(a) == 123


def test_union():
    a = Union[int, str]
    b = 123
    assert isinstance(b, a)


def test_typing_module_name():
    a = Union[int, str]
    assert not inspect.isclass(a)
    assert a.__module__ == "typing"


def test_typed_dict_total():
    class Foo(TypedDict, total=False):
        foo: int
        bar: Optional[int]

    f = Foo(foo=1)
    assert "bar" not in f


def test_value_is_not_type():
    assert not inspect.isclass(123)
    assert not isinstance(123, type)


def test_type_print():
    t = Union[int, str]
    assert str(t) == "typing.Union[int, str]"


def test_type_add_property():
    class Foo:
        foo: int = 123

    f = Foo()
    setattr(f, '__desc__', "desc")
    assert getattr(f, '__desc__') == "desc"


def test_caller_module_and_spec():
    assert inspect.getargspec(inspect.getargspec) == 'getargspec'
