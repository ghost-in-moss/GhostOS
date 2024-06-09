from typing import Any, Optional

from abc import ABC, abstractmethod


class ContextException(Exception):
    pass


class ContextIsDone(ContextException):
    pass


class ContextIsCanceled(ContextIsDone):
    pass


class ContextIsTimeout(ContextIsDone):
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
        """
        是否有异常.
        """
        pass

    @abstractmethod
    def fail(self, error: Exception) -> Optional[Exception]:
        """
        接收一个异常.
        """
        pass

    @abstractmethod
    def done(self) -> bool:
        """
        ctx 已经不能再运行.
        """
        pass

    @abstractmethod
    def life_left(self) -> float:
        """
        剩余运行时间. <= 0 表示无限.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        垃圾回收.
        """
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
