from typing import Iterable, Dict, Any, Optional
from abc import ABC, abstractmethod

from ghostos.core.ghosts import Ghost, Action, ModelThought, Operator
from ghostos.core.llms import LLMApi
from ghostos.core.runtime import Event, GoThreadInfo
from ghostos.core.moss import MossCompiler, MossRuntime, PyContext
from ghostos.thoughts.basic import LLMThoughtDriver
from ghostos.framework.actions import MossAction
from ghostos.container import Provider
from pydantic import Field

__all__ = ["MossThought", "BasicMossThoughtDriver", "MossThoughtDriver", "LLMThoughtDriver"]


class MossThought(ModelThought):
    """
    The basic Thought that use moss to provide python code interface
    """

    instruction: str = Field(description="instruction of the thought")
    moss_modulename: str = Field(description="the modulename for moss pycontext.module")
    llm_api_name: str = Field(default="", description="Name of LLM API")
    debug: bool = Field(default=False, description="debug mode, if True, moss code will send to user")


class BasicMossThoughtDriver(ABC):
    """
    helpful to define other moss thought driver
    """
    moss_runtime: Optional[MossRuntime] = None

    @abstractmethod
    def init_pycontext(self) -> PyContext:
        pass

    def providers(self) -> Iterable[Provider]:
        return []

    def injections(self) -> Dict[str, Any]:
        return {}

    def prepare_moss_compiler(self, g: Ghost, compiler: MossCompiler) -> MossCompiler:
        return compiler

    def get_moss_runtime(self, g: Ghost) -> MossRuntime:
        if self.moss_runtime is not None:
            return self.moss_runtime

        thread = g.session().get_thread()
        compiler = g.moss()
        # init default pycontext
        default_pycontext = self.init_pycontext()
        compiler = compiler.join_context(default_pycontext)
        # bind msg thread
        compiler.bind(GoThreadInfo, thread)
        # join thread
        pycontext = thread.get_pycontext()
        compiler = compiler.join_context(pycontext)
        # bind providers
        for provider in self.providers():
            compiler.register(provider)

        injections = self.injections()
        if injections:
            compiler.injects(**injections)

        # prepare some default injections that main function needed, if not imported
        compiler.with_locals(Operator=Operator, Optional=Optional)
        # callback prepare
        compiler = self.prepare_moss_compiler(g, compiler)
        # compile
        runtime = compiler.compile(None)
        self.moss_runtime = runtime
        return runtime

    @abstractmethod
    def is_moss_code_delivery(self) -> bool:
        pass

    def actions(self, g: Ghost, e: Event) -> Iterable[Action]:
        runtime = self.get_moss_runtime(g)
        yield MossAction(
            moss_runtime=runtime,
            deliver=self.is_moss_code_delivery(),
        )


class MossThoughtDriver(BasicMossThoughtDriver, LLMThoughtDriver[MossThought]):

    def instruction(self, g: Ghost, e: Event) -> str:
        return self.thought.show_instruction

    def on_created(self, g: Ghost, e: Event) -> Optional[Operator]:
        session = g.session()
        thread = session.get_thread()
        pycontext = self.init_pycontext()
        thread.update_pycontext(pycontext)
        return super().on_created(g, e)

    def is_moss_code_delivery(self) -> bool:
        return self.thought.debug

    def get_llmapi(self, g: Ghost) -> LLMApi:
        llm_api_name = self.thought.llm_api_name
        return g.llms().get_api(llm_api_name)

    def init_pycontext(self) -> PyContext:
        return PyContext(
            module=self.thought.moss_modulename,
        )
