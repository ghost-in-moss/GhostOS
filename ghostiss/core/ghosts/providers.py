from typing import Optional, Type, Generic, Iterable
from abc import ABC, abstractmethod

from ghostiss.container import Container, Provider, CONTRACT
from ghostiss.core.ghosts.ghost import Ghost
from ghostiss.core.ghosts.session import Session
from ghostiss.core.messages import Messenger
from ghostiss.core.moss import MOSS
from ghostiss.core.runtime import Runtime
from ghostiss.core.runtime.threads import Threads


class GhostProvider(Generic[CONTRACT], Provider[CONTRACT], ABC):
    is_singleton = False

    def singleton(self) -> bool:
        return self.is_singleton

    def factory(self, con: Container) -> CONTRACT:
        ghost = con.force_fetch(Ghost)
        return self.generate(ghost)

    @abstractmethod
    def generate(self, g: Ghost) -> CONTRACT:
        pass


class RuntimeProvider(GhostProvider[Runtime]):
    is_singleton = True

    def contract(self) -> Type[Runtime]:
        return Runtime

    def generate(self, g: Ghost) -> Runtime:
        return g.runtime


class ThreadsProvider(GhostProvider[Threads]):
    is_singleton = True

    def generate(self, g: Ghost) -> Threads:
        return g.runtime.threads

    def contract(self) -> Type[Threads]:
        return Threads


class SessionProvider(GhostProvider[Session]):
    is_singleton = True

    def generate(self, g: Ghost) -> Session:
        return g.session

    def contract(self) -> Type[Session]:
        return Session


class MessengerProvider(GhostProvider[Messenger]):
    is_singleton = False

    def generate(self, g: Ghost) -> CONTRACT:
        return g.messenger()

    def contract(self) -> Type[CONTRACT]:
        return Messenger


class MOSSProvider(GhostProvider[MOSS]):
    is_singleton = False

    def generate(self, g: Ghost) -> MOSS:
        return g.moss()

    def contract(self) -> Type[MOSS]:
        return MOSS


GhostProviders = [
    RuntimeProvider(),
    ThreadsProvider(),
    MessengerProvider(),
    SessionProvider(),
    MOSSProvider(),
]
""" ghost.container 默认需要绑定的各种抽象. """


def bind_ghost_container(ghost: Ghost, providers: Iterable[Provider]):
    """
    为 ghost.container 做基本的绑定.
    将 ghost 必要的实现在 container 里做注册, 从而确保 Container 中可以取出大部分实现.
    而不依赖直接从 Ghost 抽象中获取.
    :param ghost:
    :param providers: 额外的 providers.
    :return:
    """
    container = ghost.container
    # 先绑定自身.
    container.set(Ghost, ghost)
    for provider in GhostProviders:
        contract = provider.contract()
        # 没有绑定过, 则二次绑定.
        if not container.bound(contract):
            container.register(provider)
    # 注册自定义的 providers.
    for provider in providers:
        container.register(provider)
    container.bootstrap()
