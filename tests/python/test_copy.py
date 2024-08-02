def test_deep_copy_type():
    class Foo:
        bar: int = 1

    from copy import deepcopy
    # 类型的深拷贝就是类型自己.
    c = deepcopy(Foo)
    assert c is Foo
