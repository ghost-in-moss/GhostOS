from typing import Any, Optional, Tuple, Dict
from abc import ABC, abstractmethod
from ghostos.core.moss.aifunc.func import AIFunc, AIFuncResult
from ghostos.core.moss.decorators import cls_source_code
from ghostos.core.moss.abc import MossCompiler
from ghostos.core.llms import LLMApi
from ghostos.core.session import MsgThread
from ghostos.container import Container

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
        Run an AIFunc subclass instance, got result and save it into the key.
        :param key: the key that ctx keep the result in multi-turns thinking.
        :param fn: instance of AIFunc that define the task.
        :return: the certain result that match AIFuncResult and is not None
        """
        pass

    @abstractmethod
    def parallel_run(self, fn_dict: Dict[str, AIFunc]) -> Dict[str, AIFuncResult]:
        """
        Run multiple AIFunc instances in parallel and save their results.
        
        :param fn_dict: A dictionary where keys are result identifiers and values are AIFunc instances.
        :return: A dictionary where keys are the same as in fn_dict and values are the corresponding AIFuncResults.
        
        This method allows for concurrent execution of multiple AIFunc instances, which can improve
        performance when dealing with independent tasks. The results are stored and can be accessed
        using the keys provided in the input dictionary.
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
