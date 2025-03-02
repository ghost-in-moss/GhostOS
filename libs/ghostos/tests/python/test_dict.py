from typing import Optional
from typing_extensions import TypedDict


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


def test_dict_sort():
    a = {3: 3, 4: 4, 1: 1, 2: 2, }
    values = sorted(a.keys())
    assert values == [1, 2, 3, 4]


def test_get_dict_by_str_type():
    class Key(str):

        def get(self, data_: dict):
            return data_.get(str(self), None)

    data = {"a": 1, "b": 2}
    assert Key("a").get(data) == 1
