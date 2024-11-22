from typing import Iterable


def test_yield_is_blocking():
    tests = []

    def foo(values: Iterable[int]) -> Iterable[int]:
        for value in values:
            yield value
        tests.append("foo")

    def bar(values: Iterable[int]) -> Iterable[int]:
        for value in values:
            yield value
        tests.append("bar")

    list(bar(foo([1, 2, 3])))
    # yield still block
    # and if upstream not iter any, the downstream function is not running.
    assert tests == ["foo", "bar"]


def test_yield_none():
    def foo():
        yield 1
        yield 2
        yield None
        print("foo")

    v = list(foo())
    assert v == [1, 2, None]

    def bar():
        try:
            yield 1
            yield 2
            return None
        finally:
            # print("bar")
            pass

    v = list(bar())
    assert v == [1, 2]


def test_yield_with_finally():
    values = []

    def foo():
        try:
            values.append(1)
            yield 1
            values.append(2)
            yield 2
        finally:
            values.append(3)

    foo()
    # finally is not called as well.
    assert values == []


# iterable can not define __awaits__
# def test_yield_is_blocking_with_none():
#     tests = []
#
#     async def foo(values: Iterable[int]) -> Iterable[int]:
#         for value in values:
#             yield value
#         tests.append("foo")
#
#     async def bar(values: Iterable[int]) -> Iterable[int]:
#         for value in values:
#             yield value
#         yield None
#         tests.append("bar")
#
#     async def main():
#         list(await bar(await foo([1, 2, 3])))
#
#     import asyncio
#     asyncio.run(main())
#     assert tests == ["foo", "bar"]


def test_yield_after_yield_from():
    def foo():
        yield from []
        yield 1

    values = list(foo())
    assert values == [1]
