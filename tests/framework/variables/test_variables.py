from ghostos.framework.variables.variables_impl import VariablesImpl
from ghostos.framework.storage import MemStorage
from pydantic import BaseModel


class Foo(BaseModel):
    a: int = 123
    b: str = 'test'


def test_variables_impl_baseline():
    variables = VariablesImpl(MemStorage())
    v = variables.save(9527, "random int")
    assert v.desc == "random int"
    got = variables.load(v.vid, int, True)
    assert got == 9527

    cases = [
        (9527, "random int", int, True),
        ("hello world", "", str, False),
        (Foo(), "", Foo, True),
        (Foo(), "", None, False),
    ]
    for case in cases:
        value, desc, expect, force = case
        v = variables.save(value, desc)
        got = variables.load(v.vid, expect, force)
        assert got == value, f"{value} != {got}"
