from typing import Dict, Any, Optional, List, Type

from ghostos.container import Container, Provider, ABSTRACT
from ghostos.core.llms import LLMApi, LLMs
from ghostos.core.moss import MossCompiler
from ghostos.core.moss.aifunc.func import AIFunc, AIFuncResult
from ghostos.core.moss.aifunc.interfaces import AIFuncManager, AIFuncCtx, AIFuncDriver
from ghostos.core.moss.aifunc.driver import DefaultAIFuncDriverImpl

__all__ = ['DefaultAIFuncManagerImpl', 'DefaultAIFuncManagerProvider']


class DefaultAIFuncManagerImpl(AIFuncManager, AIFuncCtx):

    def __init__(
            self, *,
            container: Container,
            llm_api_name: str = "",
            max_step: int = 10,
            depth: int = 0,
            default_driver: Optional[Type[AIFuncDriver]] = None
    ):
        self._container = Container(parent=container)
        self._llm_api_name = llm_api_name
        self._values: Dict[str, Any] = {}
        self._sub_managers: List[AIFuncManager] = []
        self._max_step = max_step
        self._depth = depth
        self._default_driver_type = default_driver if default_driver else DefaultAIFuncDriverImpl

    def sub_manager(self) -> "AIFuncManager":
        manager = DefaultAIFuncManagerImpl(
            container=self._container,
            llm_api_name=self._llm_api_name,
            max_step=self._max_step,
            depth=self._depth + 1,
            default_driver=self._default_driver_type,
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

    def execute(self, fn: AIFunc, quest: str) -> AIFuncResult:
        driver = self.get_driver(fn, quest)
        thread = driver.initialize()
        step = 0
        finished = False
        result = None
        while not finished:
            step += 1
            if self._max_step != 0 and step > self._max_step:
                raise RuntimeError(f"exceeded max step {self._max_step}")
            thread, result, finished = driver.think(self, thread)
            driver.on_save(manager=self, thread=thread)
            if finished:
                break
        if result is not None and not isinstance(result, AIFuncResult):
            raise RuntimeError(f"__result__ is not an AIFuncResult")
        return result

    def get_driver(self, fn: AIFunc, request: str) -> "AIFuncDriver":
        cls = fn.__class__
        if cls.__aifunc_driver__ is not None:
            return cls.__aifunc_driver__(fn, request)
        return self._default_driver_type(fn, request)

    def run(self, key: str, fn: AIFunc, request: str = "") -> AIFuncResult:
        sub_manager = self.sub_manager()
        result = sub_manager.execute(fn, request)
        self._values[key] = result
        return result

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
