def test_func_set_attr():
    setattr(test_func_set_attr, "__test__", "test")
    assert test_func_set_attr.__test__ == "test"


def test_func_args():
    def foo(bar: int, baz: str, *args, **kwargs) -> bool:
        pass

    assert foo.__annotations__['bar'] is int
    assert foo.__annotations__['return'] is bool


def test_func_iterable_args():
    def foo(*args: int) -> int:
        return len(list(args))

    value = foo(1, 2, 3, *[4, 5, 6], 7, 8, *[9])
    assert value == 9
