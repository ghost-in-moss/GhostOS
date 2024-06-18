from typing import Iterable


def test_iterable_with_yield_and_return():
    def foo():
        yield 1
        yield 2
        return 3

    r = []
    for i in foo():
        r.append(i)
    # !!! 当 return 发生时, 迭代器取不到 next 的值.
    assert r == [1, 2]


def test_iterable_with_return_first():
    def foo(a):
        yield 1
        yield 2
        if a:
            return
        yield 4

    r = []
    for i in foo(True):
        r.append(i)
    assert r == [1, 2]


def test_return_iterable():
    def foo() -> Iterable[int]:
        yield 1
        yield 2

    def bar() -> Iterable[int]:
        return foo()

    r = list(bar())
    assert r == [1, 2]
