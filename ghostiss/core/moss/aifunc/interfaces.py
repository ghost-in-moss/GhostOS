from typing import Any, Optional, Tuple, Dict
from abc import ABC, abstractmethod
from ghostiss.core.moss.aifunc.func import AIFunc, AIFuncResult
from ghostiss.core.moss.decorators import cls_source_code
from ghostiss.core.moss.abc import MossCompiler
from ghostiss.core.llms import LLMApi
from ghostiss.core.session import MsgThread
from ghostiss.container import Container
from ghostiss.contracts.logger import LoggerItf

__all__ = [
    'AIFuncManager', 'AIFuncCtx', 'AIFuncDriver'
]


@cls_source_code()
class AIFuncCtx(ABC):
    """
    System context that could execute an AIFunc and keep result in it during multi-turns thinking.
    """

    @abstractmethod
    def run(self, key: str, fn: AIFunc) -> AIFuncResult:
        """
        Run an AIFunc, got result and save it into the key.
        :param key: the key that ctx keep the result in multi-turns thinking.
        :param fn: instance of AIFunc that define the task.
        :return: the certain result from the AIFunc.
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        get a cached value by key.
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        set a value to ctx, keep it in multi-turns thinking.
        """
        pass

    @abstractmethod
    def values(self) -> Dict[str, Any]:
        """
        return all values of the AiFuncCtx
        """
        pass


class AIFuncManager(ABC):

    @abstractmethod
    def container(self) -> Container:
        """
        为 Quest 准备的 IoC 容器.
        可以用于支持 moss.
        """
        pass

    @abstractmethod
    def default_llm_api(self) -> LLMApi:
        """
        默认用于 AIFunc 的 LLMApi
        :return:
        """
        pass

    @abstractmethod
    def compiler(self) -> MossCompiler:
        """
        返回与 AIFunc 相关的 MossCompiler
        :return:
        """
        pass

    def context(self) -> AIFuncCtx:
        """
        :return: AIFuncCtx that provide AIFunc Runtime.
        """
        pass

    @abstractmethod
    def execute(self, fn: AIFunc) -> AIFuncResult:
        """
        执行一个 AIFunc, 直到拿到它的返回结果.
        """
        pass

    @abstractmethod
    def sub_manager(self) -> "AIFuncManager":
        """
        instance an sub manager to provide AIFuncCtx for sub AIFunc
        """
        pass

    @abstractmethod
    def get_driver(self, fn: AIFunc) -> "AIFuncDriver":
        """
        根据 AIFunc 实例获取 AIFuncDriver 的实例.
        :param fn:
        :return:
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        for gc
        """
        pass


class AIFuncDriver(ABC):
    """
    the driver that produce multi-turns thinking of an AIFunc.
    """

    def __init__(self, fn: AIFunc):
        self.aifunc = fn

    @abstractmethod
    def initialize(self) -> MsgThread:
        """
        initialize the AIFunc thread by quest configuration.
        """
        pass

    @abstractmethod
    def think(self, manager: AIFuncManager, thread: MsgThread) -> Tuple[MsgThread, Optional[Any], bool]:
        """
        think another round based on msg thread.
        :param manager: AIFuncManager that provide AIFunc Runtime.
        :param thread: thread that keep multi-turns thinking's history.
        :return: (updated thread, __result__, is finish)
        """
        pass

    @abstractmethod
    def on_save(self, manager: AIFuncManager, thread: MsgThread) -> None:
        """
        一切运行结束的时候, 保存 chat 数据.
        :param manager:
        :param thread:
        :return:
        """
        pass
