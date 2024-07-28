from pydantic import BaseModel, Field
from typing import TypedDict, Required, Iterable, List
from typing_extensions import Literal


def test_pydantic_new_typed_dict() -> None:
    class Foo(BaseModel):
        foo: str = Field(default="test")

    class FooDict(TypedDict):
        foo: Required[str]

    foo = Foo()
    foo2 = FooDict(**foo.model_dump())
    assert foo2["foo"] == foo.foo


def test_pydantic_support_iterable() -> None:
    def foo() -> Iterable[int]:
        yield 1
        yield 2
        yield 3

    class Foo(BaseModel):
        values: List[int]

    f = Foo(values=foo())
    assert f.values == [1, 2, 3]


def test_pydantic_const() -> None:
    class Foo(BaseModel):
        foo: Literal["test"] = Field(default="test")

    f = Foo()
    assert f.foo == "test"


def test_pydantic_exclude_defaults() -> None:
    class Foo(BaseModel):
        foo: str = Field(default="foo")
        bar: str

    f = Foo(foo="foo", bar="bar")
    d = f.model_dump(exclude_defaults=True)
    assert "foo" not in d
    assert "bar" in d


def test_recursive_exclude_defaults() -> None:
    class Bar(BaseModel):
        a: str = Field(default="a")
        b: str

    class Foo(BaseModel):
        bar: Bar

    f = Foo(bar={"a": "a", "b": "b"})
    assert f.bar.a == "a"
    assert f.bar.b == "b"
    d = f.model_dump(exclude_defaults=True)
    # 递归地去掉了默认值.
    assert "a" not in d["bar"]
    assert d["bar"]["b"] == "b"


def test_more_input():
    class Foo(BaseModel):
        foo: str

    # allow undefined input
    f = Foo(foo="test", bar="bar")
    assert f.foo == "test"
    assert not hasattr(Foo, "bar")


def test_deep_copy() -> None:
    class Bar(BaseModel):
        bar: str = "bar"

    class Foo(BaseModel):
        bars: List[Bar]

    f = Foo(bars=[Bar()])
    # without deep
    copied = f.model_copy()
    f.bars[0].bar = "baz"
    assert copied.bars[0].bar == "baz"

    # with deep
    copied = f.model_copy(deep=True)
    f.bars[0].bar = "fool"
    assert copied.bars[0].bar == "baz"


