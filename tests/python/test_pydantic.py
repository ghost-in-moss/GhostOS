from pydantic import BaseModel, Field
from typing import TypedDict, Required, Iterable, List


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
