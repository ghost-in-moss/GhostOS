from typing import Any, Optional, Tuple, Dict, Type, List
from abc import ABC, abstractmethod
from ghostos.core.aifunc.func import AIFunc, AIFuncResult
from ghostos.core.moss.decorators import cls_source_code
from ghostos.core.moss import MossCompiler, PyContext
from ghostos.core.llms import LLMApi, Chat
from ghostos.core.session import MsgThread
from ghostos.core.messages import Message, Stream
from ghostos.abc import Identifier
from ghostos.helpers import generate_import_path, uuid
from ghostos.container import Container
from ghostos.entity import EntityMeta, model_to_entity_meta
from pydantic import BaseModel, Field

__all__ = [
    'AIFunc', 'AIFuncResult',
    'AIFuncManager', 'AIFuncCtx', 'AIFuncDriver',
    'ExecFrame', 'ExecStep',
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


class ExecStep(BaseModel):
    """
    AIFunc execute in multi-turn thinking. Each turn is a step.
    """
    frame_id: str = Field(description="step id")
    depth: int = Field(description="depth of the ExecFrame")
    step_id: str = Field(default_factory=uuid, description="step id")
    chat: Optional[Chat] = Field(default=None, description="llm chat")
    messages: List[Message] = Field(default_factory=list, description="list of messages")
    code: str = Field(default="", description="the generated code of the AIFunc")
    std_output: str = Field(default="", description="the std output of the AIFunc step")
    pycontext: Optional[PyContext] = Field(default=None, default_factory=PyContext)
    error: Optional[Message] = Field(description="the error message")
    frames: List = Field(default_factory=list, description="list of ExecFrame")

    def new_frame(self, fn: AIFunc) -> "ExecFrame":
        frame = ExecFrame.from_func(
            fn,
            depth=self.depth + 1,
            parent_step_id=self.step_id,
        )
        # thread safe append
        self.frames.append(frame)
        return frame


class ExecFrame(BaseModel):
    """
    stack frame of an AIFunc execution context
    """
    frame_id: str = Field(default_factory=uuid, description="AIFunc execution id.")
    parent_step: Optional[str] = Field(default=None, description="parent execution step id")
    request: EntityMeta = Field(description="AIFunc request, model to entity")
    response: Optional[EntityMeta] = Field(None, description="AIFunc response, model to entity")
    depth: int = Field(default=0, description="the depth of the stack")
    steps: List[ExecStep] = Field(default_factory=list, description="the execution steps")

    @classmethod
    def from_func(cls, fn: AIFunc, depth: int = 0, parent_step_id: Optional[str] = None) -> "ExecFrame":
        return cls(
            request=model_to_entity_meta(fn),
            parent_step=parent_step_id,
            depth=depth,
        )

    def new_step(self) -> ExecStep:
        step = ExecStep(frame_id=self.frame_id, depth=self.depth)
        self.steps.append(step)
        return step


class AIFuncManager(ABC):
    """
    AIFuncCtx is model-oriented.
    AIFuncManager is developer (human or meta-agent) oriented

    In other words, an AIFuncCtx is the model-oriented interface of an AIFuncManager Adapter.

    the core method is `execute`, the method itself is stateless,
    but receive a state object ExecFrame to record states.

    the `AIFuncCtx.run` is stateful when it is created from a specific ExecStep
    it will create sub ExecFrame during each call, and update self ExecStep.
    """

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
    def compiler(self, step: ExecStep, upstream: Optional[Stream] = None) -> MossCompiler:
        """
        make a MossCompiler with step and upstream.
        the MossCompiler.Container() can get sub AiFuncCtx with step and upstream.
        :param step: get moss compiler with ExecStep
        :param upstream: pass upstream to sub manager
        """
        pass

    @abstractmethod
    def context(self) -> AIFuncCtx:
        """
        :return: AIFuncCtx that bind to this manager
        """
        pass

    @abstractmethod
    def execute(
            self,
            fn: AIFunc,
            frame: Optional[ExecFrame] = None,
            upstream: Optional[Stream] = None,
    ) -> AIFuncResult:
        """
        execute an AIFunc in multi-turn thinking.
        each step of the processing will record to the frame object.

        when AiFunc is running, it may generate code in which another AiFuncCtx is called.
        The called AiFuncCtx is actually from a sub manager of this one.

        -- stack    --> AIFuncManager execution --> LLM call AiFuncCtx --> Sub AIFuncManager execution
        -- actually --> AIFuncManager execution -------------------------> Sub AIFuncManager execution
        """
        pass

    @abstractmethod
    def sub_manager(self, step: ExecStep, upstream: Optional[Stream] = None) -> "AIFuncManager":
        """
        instance an sub manager to provide AIFuncCtx for sub AIFunc
        """
        pass

    @abstractmethod
    def get_driver(
            self,
            fn: AIFunc,
    ) -> "AIFuncDriver":
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


class AIFuncRepository(ABC):
    """
    Repository that register the AIFunc information, useful to recall AIFuncs
    """

    @abstractmethod
    def register(self, fn: Type[AIFunc]) -> None:
        """
        register an AIFunc class
        :param fn: AIFunc class
        """
        pass

    @classmethod
    def identify(cls, fn: Type[AIFunc]) -> Identifier:
        """
        how to identify an AIFunc
        :param fn: class
        :return: Identifier(
           id=[import path of the AiFunc, formation is f"{fn.__module}:{func.__name__}"]
        )
        """
        return Identifier(
            id=generate_import_path(fn),
            name=fn.__name__,
            description=fn.__doc__,
        )

    @abstractmethod
    def scan(self, module_name: str, recursive: bool) -> List[Identifier]:
        """
        scan a module and find AiFunc
        :param module_name:
        :param recursive:
        :return: list of AiFunc identifiers
        """
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[Identifier]:
        """
        search AiFuncs matching the query
        :param query: nature language of the query
        :param limit: numbers of results to return
        :return: list of AiFunc identifiers
        """
        pass

    @abstractmethod
    def all(self) -> List[Identifier]:
        """
        :return: all the registered AiFunc identifiers
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
    def think(
            self,
            manager: AIFuncManager,
            thread: MsgThread,
            step: ExecStep,
            upstream: Stream,
    ) -> Tuple[MsgThread, Optional[Any], bool]:
        """
        think another round based on msg thread.
        each think round must pass a ExecStep to it.

        :param manager: AIFuncManager that provide AIFunc Runtime.
        :param thread: thread that keep multi-turns thinking's history.
        :param step: execution step.
        :param upstream: upstream that can send runtime messages.
        :return: (updated thread, __result__, is finish)
        """
        pass
