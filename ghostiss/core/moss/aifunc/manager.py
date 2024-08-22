from typing import Dict, Any, Optional, List

from ghostiss.container import Container
from ghostiss.core.llms import LLMApi, LLMs
from ghostiss.core.moss import MossCompiler
from ghostiss.core.moss.aifunc.func import AIFunc, AIFuncResult
from ghostiss.core.moss.aifunc.interfaces import AIFuncManager, AIFuncCtx, AIFuncDriver
from ghostiss.core.moss.aifunc.driver import DefaultAIFuncDriverImpl

__all__ = ['DefaultAIFuncManagerImpl']


class DefaultAIFuncManagerImpl(AIFuncManager, AIFuncCtx):

    def __init__(
            self, *,
            container: Container,
            llm_api_name: str = "",
            max_step: int = 10,
            depth: int = 0
    ):
        self._container = Container(parent=container)
        self._container.set(AIFuncCtx, self)
        self._llm_api_name = llm_api_name
        self._values: Dict[str, Any] = {}
        self._sub_managers: List[AIFuncManager] = []
        self._max_step = max_step
        self._depth = depth

    def sub_manager(self) -> "AIFuncManager":
        manager = DefaultAIFuncManagerImpl(
            container=self._container,
            llm_api_name=self._llm_api_name,
            max_step=self._max_step,
            depth=self._depth + 1,
        )
        self._sub_managers.append(manager)
        return manager

    def container(self) -> Container:
        return self._container

    def default_llm_api(self) -> LLMApi:
        llms = self._container.force_fetch(LLMs)
        return llms.get_api(self._llm_api_name)

    def compiler(self) -> MossCompiler:
        return self._container.force_fetch(MossCompiler)

    def execute(self, fn: AIFunc) -> AIFuncResult:
        driver = self.get_driver(fn)
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

    def get_driver(self, fn: AIFunc) -> "AIFuncDriver":
        cls = fn.__class__
        if cls.__aifunc_driver__ is not None:
            return cls.__aifunc_driver__(fn)
        return DefaultAIFuncDriverImpl(fn)

    def run(self, key: str, fn: AIFunc) -> AIFuncResult:
        sub_manager = self.sub_manager()
        result = sub_manager.execute(fn)
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
