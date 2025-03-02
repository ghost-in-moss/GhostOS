from typing import Union, Optional
from typing_extensions import Literal, TypedDict
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


def test_attr_typehint():
    class Foo:
        foo: int = 123

    class Bar:
        foo: Foo
        bar: Union[int, str]
        car: str
        good = 1
        moon: float = 0.0

        def loo(self):
            return self.foo

    from typing import get_type_hints
    typehints = get_type_hints(Bar)
    assert typehints['foo'] is Foo
    assert typehints['bar'] == Union[int, str]
    assert typehints['car'] is str
    assert 'good' not in typehints
    assert 'loo' not in typehints


def test_literal_int():
    def foo(v: Literal[1, 2, 3]) -> int:
        return v

    a = foo(3)
    assert a == 3
