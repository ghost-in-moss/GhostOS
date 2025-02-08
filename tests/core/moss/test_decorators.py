from typing import NamedTuple, Any, Optional, List
from ghostos.core.moss.decorators import (
    source_code, cls_source_code, cls_definition, definition,
)
from ghostos.core.moss.utils import strip_source_indent
from ghostos.core.moss.prompts import reflect_code_prompt


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
    idx = 0
    for case in cases:
        prompt = reflect_code_prompt(case.value)
        assert prompt == case.expect, f"{idx} and case is {case}"
        idx += 1


@definition(doc="test")
def test_definition():
    """
    hello
    """
    prompt = reflect_code_prompt(test_definition)
    assert "pass" in prompt
    assert "test" in prompt

    # 尝试替换 doc. 必须用 force.
    # 所以 decorator 有污染效果, 还是要考虑直接用方法获取.
    wrapped = cls_definition(doc="test foo", force=True)(Foo)
    prompt = reflect_code_prompt(wrapped)
    assert "test foo" in prompt

    # 强制重写.
    t = definition(force=True)(test_definition)
    prompt = reflect_code_prompt(t)
    assert "hello" in prompt

    # 有副作用.
    prompt = reflect_code_prompt(test_definition)
    assert "hello" in prompt


def test_cls_source_code_extends():
    @cls_source_code()
    class Bar:
        bar: int = 123

    @cls_source_code()
    class BarImpl(Bar):
        bar: int = 234

    bar_prompt = reflect_code_prompt(Bar)
    assert "Bar:" in bar_prompt
    bar_impl_prompt = reflect_code_prompt(BarImpl)
    assert "BarImpl(Bar):" in bar_impl_prompt
