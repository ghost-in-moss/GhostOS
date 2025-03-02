from ghostos_common.entity import to_entity_meta, from_entity_meta
from pydantic import BaseModel


class Foo:
    foo = 1

    def __eq__(self, other):
        return self.foo == other.foo


class Baz(BaseModel):
    baz: str = "hello"


class Bar(BaseModel):
    baz: Baz


def test_entities():
    cases = [
        1,
        0.5,
        None,
        False,
        True,
        "hello world",
        [1, 2, 3, 4.5, "hello world"],
        {"a": 1, "b": 2},
        {1:"a", "b": 2},
        Foo(),
        Baz(),
    ]

    for c in cases:
        meta = to_entity_meta(c)
        value = from_entity_meta(meta)
        assert value == c, f"{c}: {value}"
