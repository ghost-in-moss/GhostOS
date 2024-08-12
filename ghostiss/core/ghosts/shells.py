from abc import ABC, abstractmethod
from typing import Optional, Type, Iterable
from ghostiss.container import Provider, Container, ABSTRACT
from ghostiss.core.llms import Chat

__all__ = ['Shell', 'ShellProvider']


class Shell(ABC):
    """
    Shell 是对端侧能力的抽象.
    这些能力不是在 Ghost 里预定义的, 而是端侧可能动态变更的.
    Shell 通过 Process 里存储的 Meta 数据实例化而来.
    当 Meta 数据变更时, Shell 的信息也应该同时变更.
    """

    @abstractmethod
    def id(self) -> str:
        pass

    @abstractmethod
    def update_chat(self, chat: Chat) -> Chat:
        """
        将端侧的信息注入到 Chat 中.
        这些讯息应该包含对自身和环境的感知信息.
        """
        pass

    @abstractmethod
    def drivers(self) -> Iterable[Type[ABSTRACT]]:
        """
        当前 Shell 可以供 Moss 调用的抽象.
        在 Shell 实例化时, 这些抽象就应该通过 Shell Provider 注册到 Container 中.
        方便对 Moss 进行依赖注入.

        经常要搭配 Moss 功能设计使用. 举个例子:
        1. 某个 moss 文件依赖 class MusicPlayer(ABC)
        2. Shell 包含了 MusicPlayer 的实现, thought 调用 moss 时实际从 Shell 里获取了实例.
        3. Shell 如果不包含这个实现, 则 thought 应该得到错误信息的提示, 得知这个抽象不存在.
        """
        pass

    @abstractmethod
    def get_driver(self, driver: Type[ABSTRACT]) -> ABSTRACT:
        """
        获取某个抽象的实例.
        """
        pass


class ShellProvider(Provider):
    """
    通过这个 provider 将 shell 持有的 driver 提供到控制反转容器里.
    """

    @classmethod
    def from_shell(cls, shell: Shell) -> Iterable["ShellProvider"]:
        for driver in shell.drivers():
            yield ShellProvider(driver)

    def __init__(self, driver: Type[ABSTRACT]):
        self.driver: Type[ABSTRACT] = driver

    def singleton(self) -> bool:
        return False

    def contract(self) -> Type[ABSTRACT]:
        return self.driver

    def factory(self, con: Container) -> Optional[ABSTRACT]:
        shell = con.force_fetch(Shell)
        # 返回 shell driver 的实例.
        # todo: 如果不存在应该抛出特殊的异常.
        return shell.get_driver(driver=self.driver)
