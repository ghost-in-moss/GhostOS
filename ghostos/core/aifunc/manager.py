import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from typing import Dict, Any, Optional, List, Type

from ghostos.container import Container, Provider, ABSTRACT
from ghostos.core.llms import LLMApi, LLMs
from ghostos.core.moss import MossCompiler
from ghostos.core.aifunc.func import AIFunc, AIFuncResult, get_aifunc_result_type
from ghostos.core.aifunc.interfaces import AIFuncManager, AIFuncCtx, AIFuncDriver
from ghostos.core.aifunc.driver import DefaultAIFuncDriverImpl
from ghostos.core.session import MsgThread
from ghostos.helpers import generate_import_path, uuid

__all__ = ['DefaultAIFuncManagerImpl', 'DefaultAIFuncManagerProvider']


class DefaultAIFuncManagerImpl(AIFuncManager, AIFuncCtx):

    def __init__(
            self, *,
            container: Container,
            default_driver: Optional[Type[AIFuncDriver]] = None,
            llm_api_name: str = "",
            max_step: int = 10,
            depth: int = 0,
            max_depth: int = 10,
            parent_idx: str = "",
            sibling_idx: int = 0,
            aifunc_name: str = "",
            exec_id: str = "",
            parent_aifunc_name: str = "",
    ):
        self._container = Container(parent=container)
        self._llm_api_name = llm_api_name
        self._values: Dict[str, Any] = {}
        self._sub_managers: List[AIFuncManager] = []
        self._max_step = max_step
        self._depth = depth
        self._max_depth = max_depth
        if self._depth > self._max_depth:
            raise RuntimeError(f"AiFunc depth {self._depth} > {self._max_depth}, stackoverflow")
        self._default_driver_type = default_driver if default_driver else DefaultAIFuncDriverImpl
        self._exec_id = exec_id if exec_id else uuid()
        self._parent_idx = parent_idx
        self._sibling_idx = sibling_idx
        if parent_idx:
            self._identity_prefix = f"{self._parent_idx}_{self._sibling_idx}"
        else:
            self._identity_prefix = "s"
        self._aifunc_name = aifunc_name
        self._parent_aifunc_name = parent_aifunc_name
        self._child_idx = 0

    def sub_manager(self, *, aifunc_name: str = "") -> "AIFuncManager":
        self._child_idx += 1
        manager = DefaultAIFuncManagerImpl(
            container=self._container,
            default_driver=self._default_driver_type,
            llm_api_name=self._llm_api_name,
            max_step=self._max_step,
            depth=self._depth + 1,
            max_depth=self._max_depth,
            parent_idx=self._identity_prefix,
            sibling_idx=self._child_idx,
            aifunc_name=aifunc_name,
            exec_id=self._exec_id,
            parent_aifunc_name=self._aifunc_name,
        )
        self._sub_managers.append(manager)
        return manager

    def container(self) -> Container:
        return self._container

    def default_llm_api(self) -> LLMApi:
        llms = self._container.force_fetch(LLMs)
        return llms.get_api(self._llm_api_name)

    def compiler(self) -> MossCompiler:
        compiler = self._container.force_fetch(MossCompiler)
        compiler.container().set(AIFuncCtx, self)
        return compiler

    def wrap_thread(self, thread: MsgThread, aifunc_driver: AIFuncDriver) -> MsgThread:
        aifunc = aifunc_driver.aifunc
        thread.extra["aifunc"] = generate_import_path(type(aifunc))
        thread.extra["aifunc_data"] = aifunc.model_dump(exclude_defaults=True)
        thread.extra["parent_aifunc"] = self._parent_aifunc_name
        thread.extra["aifunc_depth"] = self._depth
        aifunc_name = type(aifunc).__name__
        thread.save_file = f"aifunc_{self._exec_id}/{self._identity_prefix}_{aifunc_name}.yml"
        return thread

    def execute(self, fn: AIFunc) -> AIFuncResult:
        self._aifunc_name = generate_import_path(type(fn))
        driver = self.get_driver(fn)
        thread = driver.initialize()
        thread = self.wrap_thread(thread, driver)
        step = 0
        finished = False
        result = None
        while not finished:
            step += 1
            if self._max_step != 0 and step > self._max_step:
                raise RuntimeError(f"exceeded max step {self._max_step}")
            turn = thread.last_turn()
            turn.extra["aifunc_step"] = step
            thread, result, finished = driver.think(self, thread)
            driver.on_save(manager=self, thread=thread)
            if finished:
                break
        if result is not None and not isinstance(result, AIFuncResult):
            result_type = get_aifunc_result_type(type(fn))
            raise RuntimeError(f"result is invalid AIFuncResult {type(result)}, expecting {result_type}")
        return result

    def get_driver(self, fn: AIFunc) -> "AIFuncDriver":
        cls = fn.__class__
        if cls.__aifunc_driver__ is not None:
            return cls.__aifunc_driver__(fn)
        return self._default_driver_type(fn)

    def run(self, key: str, fn: AIFunc) -> AIFuncResult:
        aifunc_name = generate_import_path(type(fn))
        sub_manager = self.sub_manager(aifunc_name=aifunc_name)
        result = sub_manager.execute(fn)
        self._values[key] = result
        return result

    def parallel_run(self, fn_dict: Dict[str, AIFunc]) -> Dict[str, AIFuncResult]:
        def execute_task(key: str, fn: AIFunc):
            aifunc_name = generate_import_path(type(fn))
            sub_manager = self.sub_manager(aifunc_name=aifunc_name)
            return key, sub_manager.execute(fn)

        results = {}
        # todo: get pool from container
        # pool = self._container.force_fetch(Pool)
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
        for manager in self._sub_managers:
            manager.destroy()
        del self._sub_managers
        self._container.destroy()
        del self._container
        del self._values


class DefaultAIFuncManagerProvider(Provider):

    def __init__(self, llm_api_name: str = ""):
        self._llm_api_name = llm_api_name

    def singleton(self) -> bool:
        return False

    def contract(self) -> Type[ABSTRACT]:
        return AIFuncManager

    def factory(self, con: Container) -> Optional[ABSTRACT]:
        return DefaultAIFuncManagerImpl(
            container=con,
            llm_api_name=self._llm_api_name,
        )
