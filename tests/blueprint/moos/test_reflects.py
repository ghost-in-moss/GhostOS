from abc import ABC, abstractmethod
from ghostiss.blueprint.moos.reflect import *
from typing import Dict, NamedTuple


class Foo(ABC):
    @abstractmethod
    def foo(self) -> str:
        """
        world
        """
        pass


class Foo1(Foo):
    def foo(self) -> str:
        """
        hello world
        """
        return "foo"


def test_attr_baseline():
    a = Attr(name="a", value=123)
    expect = """
a: int
"""
    assert a.prompt() == expect.strip()

    a = Attr(name="a", value=123, print_val=True, doc="test")
    expect = """
a: int = 123
\"""test\"""
"""
    assert a.prompt() == expect.strip()

    # 学习 golang 的写法.
    Case = NamedTuple('Case', [('a', Attr), ('expect', str)])
    cases: List[Case] = [
        Case(
            Attr(name="a", value={}, typehint=Dict[str, str]),
            """
a: typing.Dict[str, str]
"""
        ),
        Case(
            Attr(name="a", value={}, typehint=Dict[str, str], module="foo", module_spec="bar"),
            """
# from foo import bar as a
a: typing.Dict[str, str]
"""
        ),
        Case(
            Attr(name="bar", value={}, typehint=Dict[str, str], module="foo", module_spec="bar"),
            """
# from foo import bar
bar: typing.Dict[str, str]
"""
        ),
        Case(
            Attr(name="foo", value=Foo1(), typehint="Foo", module="foo", module_spec="foo"),
            """
# from foo import foo
foo: Foo
"""
        )

    ]

    for c in cases:
        assert c.a.prompt() == c.expect.strip()


def test_class_prompter():
    Case = NamedTuple('Case', [('a', Class), ('expect', str)])
    c = Case(
        Library(
            cls=Foo1,
            doc="test",
        ),
        """
class Foo1(Foo):
    \"""
    test
    \"""

    def foo(self) -> str:
        \"""
        hello world
        \"""
        pass
""",
    )
    assert c.a.prompt() == c.expect.strip()

    c = Case(
        Library(
            cls=Foo1,
            doc="test",
            methods=[],
        ),
        """
class Foo1(Foo):
    \"""
    test
    \"""
""",
    )
    assert c.a.prompt() == c.expect.strip()

    c = Case(
        Library(
            cls=Foo,
            doc="",
        ),
        """
class Foo(ABC):
    def foo(self) -> str:
        \"""
        world
        \"""
        pass
""",
    )
    assert c.a.prompt() == c.expect.strip()

    c = Case(
        Library(
            cls=Foo,
            doc="",
            methods=[],
        ),
        """
class Foo(ABC):
    pass
""",
    )
    assert c.a.prompt() == c.expect.strip()
