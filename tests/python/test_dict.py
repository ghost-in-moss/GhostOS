from typing import TypedDict, Optional


def test_dict_items():
    a = {1: 2, 3: 4}
    for k, v in a.items():
        assert k == 1
        assert v == 2
        break


def test_typed_dict_with_optional():
    class Foo(TypedDict, total=False):
        a: Optional[int]

    foo = Foo()
    assert "a" not in foo
    assert foo.get("a", None) is None


def test_dict_update():
    a = {"foo": "foo", "bar": "bar"}
    a.update(zoo="zoo")
    assert a["zoo"] == "zoo"
    a.update({"cool": "cool"})
    assert a["cool"] == "cool"
    a.update([("loo", "loo")])
    assert a["loo"] == "loo"


def test_typed_dict_with_undefined():
    class Foo(TypedDict, total=False):
        a: Optional[int]

    # typed script do not validate values
    foo = Foo(a=1, b=2)
    assert "b" in foo

    class Bar(TypedDict, total=True):
        a: Optional[int]

    bar = Bar(a=None)
    assert "a" in bar
    assert bar["a"] is None
    bar = Bar(b=1)
    assert "b" in bar

    bar2 = Bar(a="world")
    assert "a" in bar2
