from typing import List
from typing_extensions import TypedDict, Required, Self


def test_recursive_typed_dict():
    class SubPath(TypedDict, total=False):
        path: Required[str]
        desc: str
        is_dir: Required[bool]
        children: List[Self]

    s = SubPath(
        path="path",
        desc="desc",
        is_dir=True,
        children=[
            dict(
                path="path",
                is_dir=True,
            )
        ]
    )

    assert s["path"] == "path"
    assert "desc" not in s["children"][0]
    assert "children" not in s["children"][0]


def test_typeddict_module_and_name():
    class SubPath(TypedDict, total=False):
        foo: int

    assert SubPath.__module__ is not None
    assert SubPath.__name__ is not None


def test_named_tuple():
    from typing import NamedTuple
    class Foo(NamedTuple):
        foo: int

    assert Foo.__module__ is not None
    assert Foo.__name__ is not None
