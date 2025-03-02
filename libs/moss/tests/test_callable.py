from abc import abstractmethod
import inspect
from ghostos_moss.utils import *


def test_get_callable_definition():
    def foo() -> str:
        """
        test
        """
        return 'foo'

    assert get_callable_definition(foo) == """
def foo() -> str:
    \"""
    test
    \"""
    pass
""".strip()

    assert get_callable_definition(foo, alias="hello") == """
def hello() -> str:
    \"""
    test
    \"""
    pass
""".strip()

    assert get_callable_definition(foo, alias="hello", doc="") == """
def hello() -> str:
    pass
""".strip()

    assert get_callable_definition(foo, alias="hello", doc="world") == """
def hello() -> str:
    \"""
    world
    \"""
    pass
""".strip()


class Foo:

    def foo(self):
        return self

    @staticmethod
    def bar():
        return ""

    @classmethod
    def zoo(cls):
        return cls

    def cool(
            self,
            a: int,
            b: str,
    ) -> str:
        return ""

    @abstractmethod
    def do(self) -> str:  # test
        pass

    def doc(self) -> str:
        """
        test
        """
        return ""


def test_count_source_indent():
    import inspect
    source = inspect.getsource(Foo.foo)
    f = Foo()
    assert count_source_indent(source) == 4
    assert count_source_indent(inspect.getsource(Foo.bar)) == 4
    assert count_source_indent(inspect.getsource(f.zoo)) == 4


def test_strip_source_indent():
    f = Foo()
    assert strip_source_indent(inspect.getsource(f.foo)).startswith("def foo(")
    assert strip_source_indent(inspect.getsource(f.bar)).startswith("@staticmethod")
    assert strip_source_indent(inspect.getsource(f.zoo)).startswith("@classmethod")


def test_get_callable_definition_with_class():
    f = Foo()
    define = get_callable_definition(f.cool)
    expect = """
def cool(
        self,
        a: int,
        b: str,
) -> str:
    pass
"""
    assert define == expect.strip()

    # 包含 @staticmethod
    define = get_callable_definition(f.bar)
    expect = """
@staticmethod
def bar():
    pass
"""
    assert define == expect.strip()

    define = get_callable_definition(f.foo)
    expect = """
def foo(self):
    pass
"""
    assert define == expect.strip()

    # 删除了 @abstract
    define = get_callable_definition(Foo.do)
    expect = """
def do(self) -> str:  # test
    pass
"""
    assert define == expect.strip()

    define = get_callable_definition(Foo.do, "test")
    expect = """
def test(self) -> str:  # test
    pass
"""
    assert define == expect.strip()

    define = get_callable_definition(f.doc, "test")
    expect = '''
def test(self) -> str:
    """
    test
    """
    pass
'''
    assert define == expect.strip()

    define = get_callable_definition(f.doc, "test", doc="hello\nworld")
    expect = '''
def test(self) -> str:
    """
    hello
    world
    """
    pass
'''
    assert define == expect.strip()


def test_class_callable():
    class Bar:
        """
        good
        """

        def __call__(self, a: int, b: int) -> int:
            return a + b

    expect = """
def Bar(self, a: int, b: int) -> int:
    \"""
    good
    \"""
    pass
"""
    bar = Bar()
    assert get_callable_definition(bar) == expect.strip()


def test_get_callable_definition_with_abstractmethod():
    from abc import abstractmethod
    assert not inspect.isbuiltin(abstractmethod)
    code = get_callable_definition(abstractmethod)
    assert code != ""
