from abc import ABC, abstractmethod
from typing import Type, Iterable
from ghostos.container import ABSTRACT
from ghostos.core.llms import Chat, ChatPreparer
from ghostos.core.ghosts.actions import Action
from ghostos.abc import Identifiable

__all__ = ['Shell']


# class Env(Identifiable, ABC):
#     """
#     对环境抽象的感知.
#     """
#
#     @abstractmethod
#     def update_chat(self, chat: Chat) -> Chat:
#         pass
#
#     @abstractmethod
#     def driver(self) -> Type[ABSTRACT]:
#         pass
#
#     @abstractmethod
#     def provide(self) -> ABSTRACT:
#         pass


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
    def shell_prompt(self) -> str:
        """
        将端侧的信息注入到 Chat 中.
        这些讯息应该包含对自身和环境的感知信息.
        """
        pass

    @abstractmethod
    def actions(self) -> Iterable[Action]:
        """
        actions from the shell
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

