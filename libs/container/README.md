# GhostOS Container

IoC container for [GhostOS](https://github.com/ghost-in-moss/GhostOS). 

# IoC Container

`GhostOS` follows the concept of `interface-oriented programming` to build the project.
Most modules are divided into `interface` and `implementation`.
Register and get implementations by IoC Container.

About IoC: [Inverse of Control](https://en.wikipedia.org/wiki/Inversion_of_control)

## Why?

In Java and PHP projects, IoC Container is widely used. For example:

* [Java Spring](https://docs.spring.io/spring-framework/docs/3.2.x/spring-framework-reference/html/beans.html)
* [PHP Laravel](https://laravel.com/docs/11.x/container)

However, in Python projects, it is rarely used, often replaced by singletons and factory methods.

`GhostOS` introduces the `IoC Container`, with the most fundamental motivation
being to achieve `interface-oriented programming` and `runtime dependency injection`. Taking SpheroBoltGPT as an
example:

```python
from ghostos.prototypes.spherogpt.bolt import (
    RollFunc,
    Ball,
    Move,
    LedMatrix,
    Animation,
)
from ghostos_moss import Moss as Parent


class Moss(Parent):
    body: Ball
    """your sphero ball body"""

    face: LedMatrix
    """you 8*8 led matrix face"""
```

这部分代码会被自动反射成 prompt 提供给大模型. 但其中的 `Ball` 和 `LedMatrix` 在项目正式启动前都不应该实例化.
尤其是当一个 Meta-Agent 需要分析这段代码时, 它不应该在阅读代码时导致创建和 Sphero Bolt 的连接.

所以 `Ball` 和 `LedMatrix` 可以用抽象来设计:

This part of the code will be automatically reflected as a prompt provided to the large language model.
However, `Ball` and `LedMatrix` should not be instantiated before the project officially starts.

Especially when a Meta-Agent needs to analyze this code,
it should not cause the creation of a connection with `Sphero Bolt` while reading the code.
Therefore, `Ball` and `LedMatrix` can be designed abstractly:

```python
class Ball(ABC):
    """
    Sphero bolt body (which is a rolling ball) control interface.
    """

    @abstractmethod
    def new_move(
            self,
            *,
            run: bool = False,
            animation: Optional[Animation] = None,
    ) -> Move:
        """
        create a new Move instance, to define a sequence of movements.
        :param run: run immediately if True, otherwise the move will not execute until run it.
        :param animation: if animation is not none, it will be played while run the move.
        """
        pass

    @abstractmethod
    def run(self, move: Move, stop_at_first: bool = True) -> None:
        """
        run the bolt ball movement
        :param move: the Move instance that defined the movements by calling it methods one by one.
        :param stop_at_first: shall stop any movement of the ball before executing the new move?
        """
        pass
```

The actual instances are only injected through the container during runtime:

![ioc container](../../assets/ioc_container.png)

## Basic Usage

```python
from abc import ABC, abstractmethod
from typing import Type
from ghostos_container import Container, Provider


def test_container_baseline():
    class Abstract(ABC):
        @abstractmethod
        def foo(self) -> int:
            pass

    class Foo(Abstract):
        count = 0

        def foo(self) -> int:
            self.count += 1
            return self.count

    container = Container()

    # set instance
    foo = Foo()
    container.set(Foo, foo)
    assert container.get(Foo) is foo
```

## Provider

Implementations registered through the `Container.set` method are singletons.
In scenarios oriented towards composition,
a factory method is needed to obtain dependencies and generate instances.
In this case, `ghostos_container.Provider` can be used:

```python
from abc import ABC, abstractmethod
from typing import Type
from ghostos_container import Container, Provider


def test_container_baseline():
    class Abstract(ABC):
        @abstractmethod
        def foo(self) -> int:
            pass

    class Foo(Abstract):
        def __init__(self, count):
            self.count = count

        def foo(self) -> int:
            return self.count

    class FooProvider(Provider):

        def singleton(self) -> bool:
            return True

        def contract(self) -> Type[Abstract]:
            return Abstract

        def factory(self, con: Container) -> Abstract:
            # get dependencies from con
            count = con.get("count")
            return Foo(count)

    # register
    container = Container()
    container.set("count", 123)
    container.register(FooProvider())

    # get instance
    foo = container.force_fetch(Abstract)
    assert isinstance(foo, Foo)
    assert foo.foo() is 123
```

And syntax sugar `ghostos_container.provide` could decorate a factory function into a `Provider`.

```python
from abc import ABC, abstractmethod
from ghostos_container import Container, provide


class Abstract(ABC):
    @abstractmethod
    def foo(self) -> int:
        pass


class Foo(Abstract):
    def __init__(self, count):
        self.count = count

    def foo(self) -> int:
        return self.count


@provide(Abstract, singleton=True)
def foo_factory(self, con: Container) -> Abstract:
    # get dependencies from con
    count = con.get("count")
    return Foo(count)


# register
container = Container()
container.set("count", 123)
container.register(foo_factory)

# get instance
foo = container.force_fetch(Abstract)
assert isinstance(foo, Foo)
assert foo.foo() is 123
```

## Inheritance

`Container` is inheritable:

```python
from ghostos_container import Container

container = Container(name="parent")
container.set("foo", "foo")

child_container = Container(parent=container, name="child")
assert child_container.get("foo") == "foo"
```

When a descendant Container looks for a registered dependency and does not find it,
it will recursively search for it in the parent Container.

And `Provider` can also be inherited by child container:

```python
from ghostos_container import Provider


class MyProvider(Provider):

    def inheritable(self) -> bool:
        return not self.singleton()
```

All inheritable providers registered in the parent container are also automatically registered in the child container.

## Bootstrap and Shutdown

A `Container` can also serve as a container for starting and shutting down components.

```python
from ghostos_container import Bootstrapper, Container

container = Container()


class MyBootstrapper(Bootstrapper):
    def bootstrap(self, container: Container) -> None:
        # do something 
        ...


# start all the bootstrapper
container.bootstrap()
```

`Bootstrapper` can also be defined by `ghostos_container.BootstrapProvider`.

Container use`Container.add_shutdown` register shutdown callback,
they are called when `Container.shutdown` is called.

## Container Tree

In App, there are Containers at different levels, with each Container inheriting from its parent Container and managing its own
independent set of dependencies.

* When a child Container registers dependencies, it does not pollute the parent or sibling Containers.
* When a child Container is destroyed, it does not affect the parent or sibling Containers.

In this way, Container is similar to Python `contextvars`, which can manage a separate execution context, for example:

* Process level
* Thread level
* Coroutine level