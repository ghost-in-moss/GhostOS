from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Dict, get_args, get_origin

from ghostos.container import Container, Provider, ABSTRACT


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
