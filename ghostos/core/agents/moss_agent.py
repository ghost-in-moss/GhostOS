from typing import Union, Optional, Protocol, Dict, Any, TypeVar
from types import ModuleType
from abc import ABC, abstractmethod
from ghostos.common import Identifier
from pydantic import BaseModel, Field

from ghostos.helpers import import_from_path, generate_import_path
from ghostos.core.abcd import GhostDriver, Operator, Agent
from ghostos.core.runtime import Event, Runtime
from ghostos.core.moss import MossCompiler, PyContext
from .utils import make_agent_task_id


class MossAgent(BaseModel, Agent):
    """
    Basic Agent that turn a python module into a conversational agent.
    """

    Artifact = None
    """ subclass of MossAgent could have a GoalType, default is None"""

    Props = None
    """ subclass of MossAgent could have a ContextType, default is None"""

    moss_module: str = Field(description="Moss module name for the agent")
    instruction: str = Field(description="The instruction that the agent should follow")

    persona: str = Field(default="", description="Persona for the agent, if not given, use global persona")
    name: str = Field(default="", description="name of the agent")
    description: str = Field(default="", description="description of the agent")
    compile_module: Optional[str] = Field(None, description="Compile module name for the agent")
    llmapi_name: str = Field(default="", description="name of the llm api, if none, use default one")

    def __identifier__(self) -> Identifier:
        name = self.name if self.name else self.moss_module
        return Identifier(
            id=self.moss_module,
            name=name,
            description=self.description,
        )

M = TypeVar("M", bound=MossAgent)

class Moss(Protocol):
    pass


# <moss-hide>

__agent__: Optional[MossAgent] = None
""" magic attr that predefine an agent of the module with given persona and instruction."""


def __agent_moss_injections__(agent: MossAgent, session: Session) -> Dict[str, Any]:
    """
    manually define some of the injections to the Moss Class.
    if a property of Moss is not injected here, the session container will inject it by typehint.
    :param agent:
    :param session:
    """
    return {
    }


def __agent_context_prompt__(agent: MossAgent, moss: Moss) -> str:
    return ""


def __agent_goal__(agent: MossAgent, moss: Moss):
    """
    get the agent goal, default is None
    """
    return None


def __agent_on_event_type__(agent: MossAgent, session: Session, moss: Moss):
    pass


class MossAgentDriver(GhostDriver[MossAgent]):

    def make_task_id(self, runtime: Runtime, parent_task_id: Optional[str] = None) -> str:
        return make_agent_task_id(runtime, self.ghost, parent_task_id)

    def get_module(self) -> ModuleType:
        m = import_from_path(self.ghost.moss_module)
        return m

    def get_goal(self, session: Session) -> Optional[MossAgent.GoalType]:
        m = self.get_module()
        fn = __agent_goal__
        if __agent_goal__.__name__ in m.__dict__:
            fn = getattr(m, __agent_goal__.__name__)
        return fn(self.ghost, session)

    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        compiler = self.get_compiler(session)
        with compiler:
            rtm = compiler.compile(self.ghost.compile_module)
            with rtm:
                moss = rtm.moss()

    def get_compiler(self, session: Session) -> MossCompiler:
        pycontext = self.get_pycontext(session)
        compiler = session.container().force_fetch(MossCompiler)
        compiler = compiler.join_context(pycontext)
        compiler = compiler.with_locals(Optional=Optional)

        # bind moss agent itself
        compiler.bind(type(self.ghost), self.ghost)

        # bind agent level injections.
        injection_fn = __agent_moss_injections__
        module = self.get_module()
        if __agent_moss_injections__.__name__ in module.__dict__:
            injection_fn = getattr(module, __agent_moss_injections__.__name__)
        injections = injection_fn(self.ghost, session)
        compiler = compiler.injects(**injections)

        return compiler

    def get_pycontext(self, session: Session) -> PyContext:
        pycontext_key = generate_import_path(PyContext)
        data = session.properties.get(pycontext_key, None)
        if data is not None:
            pycontext = PyContext(**data)
        else:
            pycontext = PyContext(
                module=self.get_module(),
            )
        return pycontext

# </moss-hide>
