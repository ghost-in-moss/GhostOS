from abc import ABC, abstractmethod
from typing import Any, Optional, Iterator, ClassVar

from .errors import RuntimeInfo

"""
考虑引入一个 Ctx, 用来方便在上下文中传递这个框架无法感知的数据. 

- 希望下游可以用 with ctx: 的方式来使用它. 甚至放入到一个循环里. 
- 父不知子, 子知道父.  

"""


class ContextIsDone(RuntimeInfo):
    pass


class ContextIsCanceled(ContextIsDone):
    pass


class ContextIsFailed(ContextIsDone):
    pass


class Context(ABC):
    """
    考虑像 golang 一样提供一个 context 方便一些全局参数的传递.
    理论上要实现 with ctx.alive() as xxx.
    是否要实现 context.done 则需要调研一下, 最好看看 python 有没有好的 context 项目.

    todo: 有很大风险, 如果垃圾回收拉胯, 则所有代码都要修改了.
    """

    _err: Optional[Exception] = None

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def err(self) -> Optional[Exception]:
        pass

    @abstractmethod
    def fail(self, error: Exception) -> bool:
        pass

    @abstractmethod
    def cancel(self) -> None:
        pass

    @abstractmethod
    def done(self) -> bool:
        pass

    # @abstractmethod
    # def destroy(self) -> None:
    #     """
    #     主动销毁持有变量, 避免内存泄漏.
    #     """
    #     pass

    def __enter__(self):
        e = self.err()
        if e is not None:
            raise e
        if self.done():
            raise ContextIsDone("context already done")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # todo: 要不要在这里做垃圾回收的动作?
        if exc_type is None:
            return True
        elif isinstance(exc_val, ContextIsDone):
            return True
        else:
            return self.fail(exc_val)
