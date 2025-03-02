from typing import Any, Optional, Tuple, Dict, Type, List, Iterable, Callable
from abc import ABC, abstractmethod
from ghostos.core.aifunc.func import AIFunc, AIFuncResult
from ghostos_moss import MossCompiler, PyContext
from ghostos.core.llms import LLMApi, Prompt
from ghostos.core.runtime import GoThreadInfo
from ghostos.core.messages import Message, Stream, Payload
from ghostos_common.identifier import Identifier
from ghostos_common.helpers import generate_import_path, uuid
from ghostos_container import Container
from ghostos_common.entity import EntityMeta, to_entity_meta, get_entity
from pydantic import BaseModel, Field

__all__ = [
    'AIFunc', 'AIFuncResult',
    'AIFuncExecutor', 'AIFuncCtx', 'AIFuncDriver',
    'AIFuncRepository',
    'ExecFrame', 'ExecStep',
    'TooManyFailureError',
]


class TooManyFailureError(RuntimeError):
    pass


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
        :exception: TooManyFailureError
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


class ExecStepPayload(Payload):
    key = "AIFuncExecStep"
    func: str = Field(description="AIFunc name")
    frame_id: str = Field(description="execution id")
    step_id: str = Field(description="step id")


class ExecStep(BaseModel):
    """
    AIFunc execute in multi-turn thinking. Each turn is a step.
    """
    frame_id: str = Field(description="step id")
    func: str = Field(description="AIFunc name")
    depth: int = Field(description="depth of the ExecFrame")
    step_id: str = Field(default_factory=uuid, description="step id")
    chat: Optional[Prompt] = Field(default=None, description="llm chat")
    generate: Optional[Message] = Field(default=None, description="AI generate message")
    messages: List[Message] = Field(default_factory=list, description="list of messages")
    std_output: str = Field(default="", description="the std output of the AIFunc step")
    pycontext: Optional[PyContext] = Field(default=None, description="pycontext of the step")
    error: Optional[Message] = Field(default=None, description="the error message")
    frames: List = Field(default_factory=list, description="list of ExecFrame")

    def iter_messages(self) -> Iterable[Message]:
        if self.generate:
            yield self.generate
        if self.error:
            yield self.error
        yield from self.messages

    def new_frame(self, fn: AIFunc) -> "ExecFrame":
        frame = ExecFrame.from_func(
            fn,
            depth=self.depth + 1,
            parent_step_id=self.step_id,
        )
        # thread safe append
        self.frames.append(frame)
        return frame

    def as_payload(self) -> ExecStepPayload:
        return ExecStepPayload(
            func=self.func,
            frame_id=self.frame_id,
            step_id=self.step_id,
        )

    def func_name(self) -> str:
        return self.func


class ExecFrame(BaseModel):
    """
    stack frame of an AIFunc execution context
    """
    frame_id: str = Field(default_factory=uuid, description="AIFunc execution id.")
    parent_step: Optional[str] = Field(default=None, description="parent execution step id")
    args: EntityMeta = Field(description="AIFunc request, model to entity")
    result: Optional[EntityMeta] = Field(None, description="AIFunc response, model to entity")
    depth: int = Field(default=0, description="the depth of the stack")
    steps: List[ExecStep] = Field(default_factory=list, description="the execution steps")
    error: Optional[Message] = Field(default=None, description="the error message")

    @classmethod
    def from_func(cls, fn: AIFunc, depth: int = 0, parent_step_id: Optional[str] = None) -> "ExecFrame":
        return cls(
            args=to_entity_meta(fn),
            parent_step=parent_step_id,
            depth=depth,
        )

    def func_name(self) -> str:
        return self.args['type']

    def get_args(self) -> AIFunc:
        return get_entity(self.args, AIFunc)

    def set_result(self, result: AIFuncResult) -> None:
        self.result = to_entity_meta(result)

    def get_result(self) -> Optional[AIFuncResult]:
        if self.result is None:
            return None
        return get_entity(self.result, AIFuncResult)

    def new_step(self) -> ExecStep:
        step = ExecStep(
            frame_id=self.frame_id,
            func=self.args['type'],
            depth=self.depth,
        )
        self.steps.append(step)
        return step

    def last_step(self) -> Optional[ExecStep]:
        if len(self.steps) == 0:
            return None
        return self.steps[-1]


class AIFuncExecutor(ABC):
    """
    AIFuncCtx is model-oriented.
    AIFuncExecutor is developer (human or meta-agent) oriented

    In other words, an AIFuncCtx is the model-oriented interface of an AIFuncExecutor Adapter.

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

        -- stack    --> AIFuncExecutor execution --> LLM call AiFuncCtx --> Sub AIFuncExecutor execution
        -- actually --> AIFuncExecutor execution -------------------------> Sub AIFuncExecutor execution
        """
        pass

    def new_exec_frame(self, fn: AIFunc, upstream: Stream) -> Tuple[ExecFrame, Callable[[], AIFuncResult]]:
        """
        syntax sugar
        """
        frame = ExecFrame.from_func(fn)

        def execution() -> AIFuncResult:
            with upstream:
                return self.execute(fn, frame, upstream)

        return frame, execution

    @abstractmethod
    def sub_executor(self, step: ExecStep, upstream: Optional[Stream] = None) -> "AIFuncExecutor":
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
    def register(self, *fns: Type[AIFunc]) -> None:
        """
        register an AIFunc class
        :param fns: AIFunc class
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
    def scan(self, module_name: str, *, recursive: bool, save: bool) -> List[Identifier]:
        """
        scan a module and find AiFunc
        :param module_name: the modulename where an AIFunc is located or start point of a recursive search
        :param recursive: if recursive search
        :param save: if auto save to the repository
        :return: list of AiFunc identifiers
        """
        pass

    @abstractmethod
    def list(self, offset: int = 0, limit: int = -1) -> Iterable[Identifier]:
        """
        :param offset: offset of the first item in the list
        :param limit: limit the list, if limit <= 0 means return all identifiers after offset.
        :return: all the registered AiFunc identifiers
        """
        pass

    @abstractmethod
    def validate(self) -> None:
        """
        validate the registered AiFunc, remove invalid ones
        """
        pass

    @abstractmethod
    def save_exec_frame(self, frame: ExecFrame) -> None:
        pass


class AIFuncDriver(ABC):
    """
    the driver that produce multi-turns thinking of an AIFunc.
    """

    def __init__(self, fn: AIFunc):
        self.aifunc = fn

    @abstractmethod
    def initialize(self, container: Container, frame: ExecFrame) -> GoThreadInfo:
        """
        initialize the AIFunc thread by quest configuration.
        """
        pass

    @abstractmethod
    def think(
            self,
            manager: AIFuncExecutor,
            thread: GoThreadInfo,
            step: ExecStep,
            upstream: Optional[Stream],
    ) -> Tuple[GoThreadInfo, Optional[Any], bool]:
        """
        think another round based on msg thread.
        each think round must pass a ExecStep to it.

        :param manager: AIFuncExecutor that provide AIFunc Runtime.
        :param thread: thread that keep multi-turns thinking's history.
        :param step: execution step.
        :param upstream: upstream that can send runtime messages.
        :return: (updated thread, __result__, is finish)
        """
        pass

    @abstractmethod
    def on_save(self, container: Container, frame: ExecFrame, step: ExecStep, thread: GoThreadInfo) -> None:
        """
        save the status on each step
        """
        pass
