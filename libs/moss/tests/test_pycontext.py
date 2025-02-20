import json
from typing import NamedTuple, Any, List, TypedDict, Optional
from types import ModuleType
from ghostos_moss.pycontext import PyContext
from pydantic import BaseModel, Field


def test_pycontext_join_baseline():
    left = PyContext()
    left.set_prop("foo", 123)
    right = PyContext()
    right.set_prop("bar", 234)
    joined = left.join(right)
    assert len(left.properties) == 1
    assert len(right.properties) == 1
    assert len(joined.properties) == 2


class Foo(BaseModel):
    foo: int = Field(default=123)


class Bar(TypedDict, total=False):
    bar: Optional[str]


def test_property_with_values():
    case = NamedTuple("Case", [("name", str), ("value", Any)])
    cases: List[case] = [
        case("foo", 123),
        case("bar", None),
        case("a", 1.0),
        case("", False),
        case("foo", Foo()),
        case("bar", Bar(bar="hello")),
    ]
    pycontext = PyContext()
    for c in cases:
        pycontext.set_prop(c.name, c.value)
        j = pycontext.model_dump_json()
        data = json.loads(j)
        new_one = PyContext(**data)
        value = new_one.get_prop(c.name)
        assert c.value == value, j


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
    pycontext = PyContext()
    pycontext.set_prop(name="foo", value=foo)
    assert foo == pycontext.get_prop("foo", module)
    j = pycontext.model_dump(exclude_defaults=True)
    p = PyContext(**j)
    # 从当前 module 里重新还原出来.
    assert p.get_prop("foo", module) == foo
