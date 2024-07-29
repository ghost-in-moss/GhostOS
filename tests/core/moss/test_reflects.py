import inspect
from abc import ABC, abstractmethod
from ghostiss.reflect import *
from typing import Dict, NamedTuple, List


class Foo(ABC):
    @abstractmethod
    def foo(self) -> str:
        """
        world
        """
        pass


class Foo1(Foo):

    def __init__(self):
        self.bar = 123

    def foo(self) -> str:
        """
        hello world
        """
        return "foo"


def test_attr_baseline():
    a = Attr(name="a", value=123)
    expect = """
a: int = 123
"""
    # 整数类型自动打印值.
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
    pass
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

    c = Case(
        Interface(
            cls=Foo,
            doc="test",
        ),
        """
class Foo(ABC):
    \"""
    test
    \"""
    pass
""",
    )
    assert c.a.prompt() == c.expect.strip()


def test_build_class_prompt():
    builder = ClassPrompter(
        cls=Foo,
        constructor=Method(caller=Foo1.__init__),
        methods=[Method(caller=Foo1.foo)],
        attrs=[Attr(name="a", value=123)],
    )

    expect = """
class Foo(ABC):
    def __init__(self):
        pass

    a: int = 123

    def foo(self) -> str:
        \"""
        hello world
        \"""
        pass
"""
    assert builder.prompt() == expect.strip()


def test_reflect_class():
    class Xoo:
        def foo(self) -> str:
            return "foo"

    assert inspect.isclass(Xoo)

    r = reflect(var=Xoo)
    assert isinstance(r, TypeReflection)
