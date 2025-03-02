from concurrent.futures import ThreadPoolExecutor, as_completed

from typing import Dict, Any, Optional, Type, Callable, Iterable
from typing_extensions import Self

from ghostos_container import Container, Provider, ABSTRACT
from ghostos.core.llms import LLMApi, LLMs
from ghostos_moss import MossCompiler
from ghostos.core.aifunc.func import AIFunc, AIFuncResult, get_aifunc_result_type
from ghostos.core.aifunc.interfaces import AIFuncExecutor, AIFuncCtx, AIFuncDriver, ExecFrame, ExecStep
from ghostos.core.aifunc.driver import DefaultAIFuncDriverImpl
from ghostos.core.messages import Stream, MessageType

__all__ = ['DefaultAIFuncExecutorImpl', 'DefaultAIFuncExecutorProvider']


class DefaultAIFuncExecutorImpl(AIFuncExecutor, AIFuncCtx):

    def __init__(
            self, *,
            container: Container,
            step: Optional[ExecStep] = None,
            upstream: Optional[Stream] = None,
            default_driver: Optional[Type[AIFuncDriver]] = None,
            llm_api_name: str = "",
            max_depth: int = 10,
            max_step: int = 10,
    ):
        # manager do not create submanager
        # but the container of MossCompiler from this manager
        # get an instance of AIFuncCtx, which is actually submanager of this one.
        self._container = container
        self._exec_step = step
        self._upstream: Stream = upstream
        self._llm_api_name = llm_api_name
        self._values: Dict[str, Any] = {}
        self._max_depth = max_depth
        self._max_step = max_step
        if step and step.depth > self._max_depth:
            raise RuntimeError(f"AiFunc depth {step.depth} > {self._max_depth}, stackoverflow")
        self._default_driver_type = default_driver if default_driver else DefaultAIFuncDriverImpl
        self._destroyed = False

    def sub_executor(self, step: ExecStep, upstream: Optional[Stream] = None) -> "AIFuncExecutor":
        # sub manager's upstream may be None
        # parent manager do not pass upstream to submanager
        manager = DefaultAIFuncExecutorImpl(
            container=self._container,
            step=step,
            upstream=upstream,
            default_driver=self._default_driver_type,
            llm_api_name=self._llm_api_name,
            max_depth=self._max_depth,
        )
        # register submanager, destroy them together
        return manager

    def context(self) -> AIFuncCtx:
        return self

    def container(self) -> Container:
        return self._container

    def default_llm_api(self) -> LLMApi:
        llms = self._container.force_fetch(LLMs)
        return llms.get_api(self._llm_api_name)

    def compiler(self, step: ExecStep, upstream: Optional[Stream] = None) -> MossCompiler:
        compiler = self._container.force_fetch(MossCompiler)

        # rebind exec step to moss container, which is a sub container
        # the exec step will not contaminate self._container
        maker = self._sub_manager_fn(step, upstream)

        compiler.container().register_maker(
            contract=AIFuncCtx,
            maker=maker,
            singleton=True,
        )
        compiler.container().set(ExecStep, step)
        return compiler

    def _sub_manager_fn(self, step: ExecStep, upstream: Optional[Stream]) -> Callable[[], Self]:
        def sub_manager() -> AIFuncExecutor:
            return self.sub_executor(step, upstream)

        return sub_manager

    def execute(
            self,
            fn: AIFunc,
            frame: Optional[ExecFrame] = None,
            upstream: Optional[Stream] = None,
    ) -> AIFuncResult:
        try:
            if frame is None:
                frame = ExecFrame.from_func(fn)
            driver = self.get_driver(fn)
            thread = driver.initialize(self.container(), frame)
            step = 0
            finished = False
            result = None
            while not finished:
                step += 1
                # each step generate a new exec step
                exec_step = frame.new_step()
                if self._max_step != 0 and step > self._max_step:
                    raise RuntimeError(f"exceeded max step {self._max_step}")
                thread, result, finished = driver.think(self, thread, exec_step, upstream=upstream)
                driver.on_save(self.container(), frame, exec_step, thread)

                if finished:
                    break
            if result is not None and not isinstance(result, AIFuncResult):
                result_type = get_aifunc_result_type(type(fn))
                raise RuntimeError(f"result is invalid AIFuncResult {type(result)}, expecting {result_type}")

            frame.set_result(result)
            # if frame is the root, send final message as protocol
            return result
        except Exception as e:
            frame.error = MessageType.ERROR.new(content=str(e))
            raise

    def get_driver(
            self,
            fn: AIFunc,
    ) -> "AIFuncDriver":
        cls = fn.__class__
        if cls.__aifunc_driver__ is not None:
            driver = cls.__aifunc_driver__
        else:
            driver = self._default_driver_type
        return driver(fn)

    def run(self, key: str, fn: AIFunc) -> AIFuncResult:
        if self._exec_step is not None:
            frame = self._exec_step.new_frame(fn)
        else:
            frame = ExecFrame.from_func(fn)
        sub_step = frame.new_step()
        sub_manager = self.sub_executor(sub_step)
        try:
            result = sub_manager.execute(fn, frame=frame, upstream=self._upstream)
            # thread safe? python dict is thread safe
            self._values[key] = result
            return result
        finally:
            # always destroy submanager.
            # or memory leak as hell
            sub_manager.destroy()

    def parallel_run(self, fn_dict: Dict[str, AIFunc]) -> Dict[str, AIFuncResult]:
        def execute_task(key: str, fn: AIFunc):
            r = self.run(key, fn)
            return key, r

        results = {}
        with ThreadPoolExecutor(max_workers=len(fn_dict)) as executor:
            futures = [executor.submit(execute_task, key, fn) for key, fn in fn_dict.items()]
            for future in as_completed(futures):
                key, result = future.result()
                results[key] = result
                self._values[key] = result

        return results

    def get(self, key: str) -> Optional[Any]:
        return self._values.get(key, None)

    def set(self, key: str, value: Any) -> None:
        self._values[key] = value

    def values(self) -> Dict[str, Any]:
        return self._values

    def destroy(self) -> None:
        if self._destroyed:
            # destroy once.
            # not every submanager is created at self.execute,
            # so they could be destroyed outside already
            return
        self._destroyed = True
        del self._container
        del self._values
        del self._exec_step
        del self._upstream


class DefaultAIFuncExecutorProvider(Provider[AIFuncExecutor]):

    def __init__(
            self,
            llm_api_name: str = "",
    ):
        self._llm_api_name = llm_api_name

    def singleton(self) -> bool:
        # !! AIFuncManager shall not be
        return False

    def aliases(self) -> Iterable[ABSTRACT]:
        yield AIFuncCtx

    def factory(self, con: Container) -> Optional[AIFuncExecutor]:
        return DefaultAIFuncExecutorImpl(
            container=con,
            llm_api_name=self._llm_api_name,
        )
