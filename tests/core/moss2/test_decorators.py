from typing import NamedTuple, Any, Optional, List
from ghostiss.core.moss2.decorators import (
    source_code, cls_source_code, cls_definition, definition,
)
from ghostiss.core.moss2.utils import strip_source_indent
from ghostiss.core.moss2.prompts import get_prompt


class Foo:
    foo: int = 123


def test_source_code():
    import inspect

    @cls_source_code()
    class Case(NamedTuple):
        value: Any
        expect: Optional[str]

    self_source = strip_source_indent(inspect.getsource(test_source_code))
    cases: List[Case] = [
        Case(Case, strip_source_indent(inspect.getsource(Case))),
        Case(source_code()(test_source_code), self_source),
        # 预计对函数也是有副作用的.
        Case(test_source_code, self_source),
        # 预计对类有副作用.
        Case(cls_source_code()(Foo), strip_source_indent(inspect.getsource(Foo))),
        Case(Foo, strip_source_indent(inspect.getsource(Foo))),
    ]
    for case in cases:
        prompt = get_prompt(case.value)
        assert prompt == case.expect


@definition(doc="test")
def test_definition():
    """
    hello
    """
    prompt = get_prompt(test_definition)
    assert "pass" in prompt
    assert "test" in prompt

    # 尝试替换 doc. 必须用 force.
    # 所以 decorator 有污染效果, 还是要考虑直接用方法获取.
    wrapped = cls_definition(doc="test foo", force=True)(Foo)
    prompt = get_prompt(wrapped)
    assert "test foo" in prompt

    # 强制重写.
    t = definition(force=True)(test_definition)
    prompt = get_prompt(t)
    assert "hello" in prompt

    # 有副作用.
    prompt = get_prompt(test_definition)
    assert "hello" in prompt


def test_cls_source_code_extends():
    @cls_source_code()
    class Bar:
        bar: int = 123

    @cls_source_code()
    class BarImpl(Bar):
        bar: int = 234

    bar_prompt = get_prompt(Bar)
    bar_impl_prompt = get_prompt(BarImpl)
    assert "Bar:" in bar_prompt
    assert "BarImpl(Bar):" in bar_impl_prompt
