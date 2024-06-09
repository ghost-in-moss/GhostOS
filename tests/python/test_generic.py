from typing import Generic, TypeVar, Optional
from abc import ABC, abstractmethod


class FooInterface(ABC):
    @abstractmethod
    def foo(self) -> str:
        pass


F = TypeVar("F", bound=FooInterface)


class FooFactory(Generic[F]):

    def __init__(self, foo: F):
        self.foo = foo

    def get_foo(self) -> F:
        return self.foo


class FooInstance(FooInterface):

    def foo(self) -> str:
        return "hello"

    def bar(self) -> str:
        return self.foo() + " world"


def test_generic_class_ide_prediction():
    ins = FooInstance()
    factory = FooFactory[FooInstance](ins)
    foo = factory.get_foo()
    assert foo.foo() == "hello"
    # ide can predict bar() method.
    assert foo.bar() == "hello world"


C = TypeVar("C")

K = TypeVar("K")


class Operator(Generic[C, K], ABC):

    def run(self, ctx: C, kernel: K) -> Optional["Operator"]:
        return None


class IntOp(Operator[int, str]):
    pass


class StrOp(Operator[str, str]):
    pass


def test_generic_typehint_is_working():
    op = IntOp()
    # 泛型校验实际上有效果.
    assert not isinstance(op, StrOp)
    assert isinstance(op, IntOp)
    assert isinstance(op, Operator)
