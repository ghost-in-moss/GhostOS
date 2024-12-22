from collections import deque


def test_deque():
    d = deque([1, 2, 3, 4, 5])
    assert 5 == len(d)
    assert 1 == d.popleft()
    assert 5 == d.pop()
    assert d.count(5) == 0
    assert d.count(2) == 1
    d.pop()
    d.pop()
    d.pop()

    e = None
    assert len(d) == 0
    try:
        d.popleft()
    except IndexError as err:
        e = err
    assert e is not None


def test_yield_from_deque():
    d = deque([1, 2, 3, 4, 5])

    def foo(dq: deque):
        yield from dq

    assert list(foo(d)) == [1, 2, 3, 4, 5]
