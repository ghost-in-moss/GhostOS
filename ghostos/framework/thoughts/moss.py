from typing import Iterable

from ghostos.core.ghosts import Ghost, Action, ModelThought
from ghostos.core.llms import LLMApi
from ghostos.core.session import Event, MsgThread
from ghostos.core.moss import MossCompiler, MossRuntime, PyContext
from ghostos.framework.thoughts.basic import LLMThoughtDriver
from pydantic import BaseModel, Field


class MossThought(ModelThought):
    moss_modulename: str = Field(description="the modulename for moss pycontext.module")
    llm_api_name: str = Field(default="", description="Name of LLM API")


class MossThoughtDriver(LLMThoughtDriver):

    def get_llmapi(self, g: Ghost) -> LLMApi:
        pass

    def init_pycontext(self) -> PyContext:
        pass

    def prepare_moss_compiler(self, g: Ghost) -> MossCompiler:
        thread = g.session().thread()
        compiler = g.moss()
        compiler.bind(MsgThread, thread)
        compiler = compiler.join_context(thread.get_pycontext())
        return compiler

    def actions(self, g: Ghost, e: Event) -> Iterable[Action]:
        pass

    def instruction(self, g: Ghost, e: Event) -> str:
        pass
