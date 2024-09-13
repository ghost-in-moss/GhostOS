from typing import Iterable, Dict, Any, Optional
from abc import ABC, abstractmethod

from ghostos.core.ghosts import Ghost, Action, ModelThought, Operator
from ghostos.core.llms import LLMApi
from ghostos.core.session import Event, MsgThread
from ghostos.core.moss import MossCompiler, MossRuntime, PyContext
from ghostos.thoughts.basic import LLMThoughtDriver
from ghostos.framework.actions import MossAction
from ghostos.container import Provider
from pydantic import Field

__all__ = ["MossThought", "BasicMossThoughtDriver", "MossThoughtDriver"]


class MossThought(ModelThought):
    """
    The basic Thought that use moss to provide python code interface
    """

    name: str = Field(description="thought name")
    description: str = Field(description="thought description")
    instruction: str = Field(description="instruction of the thought")
    moss_modulename: str = Field(description="the modulename for moss pycontext.module")
    llm_api_name: str = Field(default="", description="Name of LLM API")
    debug: bool = Field(default=False, description="debug mode, if True, moss code will send to user")


class BasicMossThoughtDriver(ABC):
    """
    helpful to define other moss thought driver
    """

    @abstractmethod
    def init_pycontext(self) -> PyContext:
        pass

    def providers(self) -> Iterable[Provider]:
        return []

    def injections(self) -> Dict[str, Any]:
        return {}

    def prepare_moss_compiler(self, g: Ghost) -> MossCompiler:
        thread = g.session().thread()
        compiler = g.moss()
        compiler.bind(MsgThread, thread)
        pycontext = thread.get_pycontext()

        if not pycontext.module:
            pycontext = PyContext()

        compiler = compiler.join_context(pycontext)
        for provider in self.providers():
            compiler.register(provider)

        injections = self.injections()
        if injections:
            compiler.injects(**injections)

        # prepare some default injections that main function needed, if not imported
        compiler.with_locals(Operator=Operator, Optional=Optional)
        return compiler

    def get_moss_runtime(self, g: Ghost) -> MossRuntime:
        return self.prepare_moss_compiler(g).compile(None)

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
        return self.thought.instruction

    def on_created(self, g: Ghost, e: Event) -> Optional[Operator]:
        session = g.session()
        thread = session.thread()
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
