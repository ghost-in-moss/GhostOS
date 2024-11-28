from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Dict, get_args, get_origin, ClassVar

from ghostos.container import Container, Provider, provide


def test_container_baseline():
    class Abstract(metaclass=ABCMeta):
        @abstractmethod
        def foo(self) -> int:
            pass

    class Foo(Abstract):
        count = 0

        def foo(self) -> int:
            self.count += 1
            return self.count

    #
    # class TestProvider(Provider):
    #     Abstract = Abstract
    #
    #     @classmethod
    #     def factory(cls, c: Container) -> Abstract | None:
    #         return Foo()

    class FooProvider(Provider):

        def __init__(self, singleton: bool):
            self._s = singleton

        def singleton(self) -> bool:
            return self._s

        def contract(self) -> Type[Abstract]:
            return Abstract

        def factory(self, con: Container, params: Dict | None = None) -> Abstract | None:
            return Foo()

    # 初始化
    container = Container()
    container.set(Abstract, Foo())

    # 获取单例
    foo = container.fetch(Abstract)
    assert foo.foo() == 1
    foo = container.fetch(Abstract)
    assert foo.foo() == 2  # 获取的是单例
    foo = container.fetch(Abstract)
    assert foo.foo() == 3

    # 注册 provider, 销毁了单例.
    container.register(FooProvider(True))

    # 二次取值. 替换了 原始实例, 但还是生成单例.
    foo = container.force_fetch(Abstract)
    assert foo.foo() == 1
    foo = container.force_fetch(Abstract)
    assert foo.foo() == 2

    # 注册 provider, 销毁了单例. 注册的是非单例
    container.register(FooProvider(False))
    foo = container.force_fetch(Abstract)
    assert foo.foo() == 1
    # 每次都是返回新实例.
    foo = container.force_fetch(Abstract)
    assert foo.foo() == 1
    assert foo.foo() == 2


def test_sub_container():
    class Foo:
        def __init__(self, foo: int):
            self.foo = foo

    container = Container()
    container.set(Foo, Foo(1))
    sub = Container(parent=container)
    sub.set(Foo, Foo(2))

    # 验证父子互不污染.
    assert container.force_fetch(Foo).foo == 1
    assert sub.force_fetch(Foo).foo == 2


def test_boostrap():
    container = Container()

    class Foo:
        foo: int = 1

    container.set(Foo, Foo())
    container.bootstrap()
    assert container.force_fetch(Foo).foo == 1


def test_provider_generic_types():
    class SomeProvider(Provider[int]):

        def singleton(self) -> bool:
            return True

        def factory(self, con: Container) -> int:
            return 3

    # baseline
    args = get_args(Provider[int])
    assert args[0] is int
    assert get_origin(Provider[int]) is Provider

    p = SomeProvider()
    con = Container()
    assert p.singleton()
    assert p.factory(con) == 3
    assert p.contract() is int


def test_provide_with_lambda():
    container = Container()
    container.register(provide(int)(lambda c: 10))
    container.register(provide(str)(lambda c: "hello"))

    assert container.force_fetch(int) == 10
    assert container.force_fetch(str) == "hello"


def test_provide_in_loop():
    container = Container()
    for a, fn in {int: lambda c: 10, str: lambda c: "hello"}.items():
        container.register(provide(a)(fn))

    assert container.force_fetch(int) == 10
    assert container.force_fetch(str) == "hello"


def test_container_set_str():
    container = Container()
    container.set("foo", "bar")
    assert container.get("foo") == "bar"


def test_container_inherit():
    class Foo:
        def __init__(self, foo: int):
            self.foo = foo

    class Bar:
        def __init__(self, foo: Foo):
            self.foo = foo

        bar: str = "hello"

    container = Container()
    container.register(provide(Bar, singleton=False)(lambda c: Bar(c.force_fetch(Foo))))
    sub_container = Container(container)
    # sub container register Foo that Bar needed
    sub_container.register(provide(Foo, singleton=False)(lambda c: Foo(2)))
    bar = sub_container.force_fetch(Bar)
    assert bar.bar == "hello"
    assert bar.foo.foo == 2


def test_bloodline():
    container = Container()
    assert container.bloodline is not None
    sub = Container(parent=container, name="hello")
    assert len(sub.bloodline) == 2


def test_container_shutdown():
    class Foo:
        instance_count: ClassVar[int] = 0

        def __init__(self):
            Foo.instance_count += 1

        def shutdown(self):
            Foo.instance_count -= 1

    container = Container()
    f = Foo()
    container.set(Foo, f)
    container.add_shutdown(f.shutdown)
    assert Foo.instance_count == 1
    container.shutdown()
    assert Foo.instance_count == 0
