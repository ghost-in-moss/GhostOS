from typing import NamedTuple, Any, List, TypedDict, Optional
from types import ModuleType
from ghostiss.core.moss.pycontext import PyContext, Injection, Property, attr
from pydantic import BaseModel, Field


def test_pycontext_imported():
    c = PyContext()
    c.inject(Injection(import_from="foo:bar"))
    assert len(c.injections) == 1


def test_pycontext_join_baseline():
    left = PyContext()
    i = Injection.reflect(Injection)
    left.inject(i)
    right = PyContext()
    right.inject(Injection(import_from="foo:bar"))
    joined = left.join(right)
    assert len(left.injections) == 1
    assert len(right.injections) == 1
    assert len(joined.injections) == 2


class Foo(BaseModel):
    foo: int = Field(default=123)


class Bar(TypedDict, total=False):
    bar: Optional[str]


def test_property_with_values():
    case = NamedTuple("Case", [("name", str), ("value", Any), ("desc", str)])
    cases: List[case] = [
        case("foo", 123, ""),
        case("bar", None, "none"),
        case("a", 1.0, "abc"),
        case("", False, "abc"),
        case("foo", Foo(), ""),
        case("bar", Bar(), ""),
    ]
    for c in cases:
        p = Property.from_value(name=c.name, value=c.value, desc=c.desc)
        assert p.generate_value() is c.value
        assert p.name is c.name
        assert p.desc is c.desc

        j = p.model_dump(exclude_defaults=True)
        p = Property(**j)
        assert p.generate_value() == c.value
        assert p.name == c.name
        assert p.desc == c.desc


def test_property_with_local_module():
    module = ModuleType("__test__")
    code = """
from pydantic import BaseModel, Field
class Foo(BaseModel):
    foo: int = Field(default=123)
foo = Foo()
"""
    compiled = compile(code, "<test>", "exec")
    exec(compiled, module.__dict__)
    foo = module.__dict__["foo"]
    assert foo.foo == 123
    p = Property.from_value(name="foo", value=foo)
    assert foo is p.generate_value(module)
    j = p.model_dump(exclude_defaults=True)
    p = Property(**j)
    # 从当前 module 里重新还原出来.
    assert p.generate_value(module) == foo


def test_bind_property_as_attr():
    class Zoo:
        foo: Foo = attr(Foo(foo=123), desc="foo")
        bar: Optional[str] = attr(None, desc="bar")

    z = Zoo()
    assert Zoo.foo.foo is 123
    assert Zoo.bar is None
    z.bar = "bar"
    assert z.bar == "bar"
    # 给实例赋值时污染了类.
    assert Zoo.bar == "bar"

    foo_prop = Zoo.__dict__["foo"]
    assert isinstance(foo_prop, Property)
    assert foo_prop.name == "foo"

    assert str(foo_prop)
    assert f"{foo_prop}"
