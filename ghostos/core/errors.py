from typing import Optional


class GhostOSError(Exception):
    # todo: 深入理解 python exception 再实现细节.

    def __init__(self, message: str, parent: Optional[Exception] = None):
        super().__init__(message)
        self.catch = parent
        if self.catch is not None:
            # todo: 不太会用 python 的异常.
            self.__cause__ = self.catch.__cause__


class RaisedNotice(GhostOSError):
    """
    不是真正的 error, 而是用于 try catch 的一个 notice.
    """
    pass


class GhostContextError(GhostOSError):
    """
    一次运行级别的 error, 让运行无效.
    """
    pass


class GhostOSIOError(GhostOSError):
    """
    运行时的 io 异常. 通常影响的只是 context.
    """
    pass


class GhostOSRuntimeError(GhostOSError):
    """
    让一个 runtime 进程失效退出.
    """
    pass
