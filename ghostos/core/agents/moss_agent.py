from typing import Union, Optional, Protocol, Dict, Any, TypeVar, Generic, List
from types import ModuleType
from abc import ABC, abstractmethod

from ghostos.identifier import Identifier
from pydantic import BaseModel, Field

from ghostos.helpers import import_from_path, generate_import_path
from ghostos.core.abcd import GhostDriver, Operator, Agent, Session, StateValue, Action
from ghostos.core.runtime import Event, Runtime, GoThreadInfo
from ghostos.core.moss import MossCompiler, PyContext
from ghostos.core.messages import Message, Caller
from ghostos.core.llms import LLMs, LLMApi, Prompt, PromptPipe
from ghostos.container import Container
from .utils import make_agent_task_id


class MossAgent(BaseModel, Agent):
    """
    Basic Agent that turn a python module into a conversational agent.
    """

    Artifact = None
    """ subclass of MossAgent could have a GoalType, default is None"""

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


A = TypeVar("A", bound=MossAgent)


class Moss(Generic[A], ABC):
    """
    the model-oriented operating system defined in the moss module
    useful for:
    1. inject dynamic implementations by IoC Container
    2. inject session state values.

    and the state values injected to the Moss instance, will bind to the session as default.
    """

    self: A
    """self moss agent"""

    props: A.Props
    """self props"""


# --- lifecycle methods of moss agent --- #


def __agent_goal__(agent: MossAgent, moss: Moss):
    """
    get the agent goal, default is None
    """
    return None


def __agent_contextual_prompt__(agent: A, moss: Moss) -> str:
    """
    magic function that defined in the moss module, generate contextual prompt for the agent
    """
    return ""


# <moss-hide>

__agent__: Optional[MossAgent] = None
""" magic attr that predefine an agent of the module with given persona and instruction."""


def __agent_moss_injections__(agent: A, session: Session[A]) -> Dict[str, Any]:
    """
    manually define some of the injections to the Moss Class.
    if a property of Moss is not injected here, the session container will inject it by typehint.
    :param agent:
    :param session:
    """
    return {
    }


def __agent_on_event_type__(agent: A, session: Session[A], moss: Moss):
    pass


class MossAgentDriver(GhostDriver[MossAgent]):

    def get_module(self) -> ModuleType:
        m = import_from_path(self.ghost.moss_module)
        return m

    def get_goal(self, session: Session) -> Optional[MossAgent.GoalType]:
        m = self.get_module()
        if __agent_goal__.__name__ not in m.__dict__:
            return None
        fn = getattr(m, __agent_goal__.__name__)
        compiler = self.get_compiler(session)
        with compiler:
            runtime = compiler.compile(self.ghost.moss_module)
            with runtime:
                moss = runtime.moss()
                return fn(self.ghost, moss)

    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        event = self.filter_event(session, event)
        if event is None:
            return None

        thread = self.update_with_event(session, event)

        compiler = self.get_compiler(session)
        with compiler:
            rtm = compiler.compile(self.ghost.compile_module)
            with rtm:
                moss = rtm.moss()
                # prepare instructions.
                instructions = self.get_instructions(session, moss)
                # prepare prompt
                prompt = thread.to_prompt(instructions)
                prompt = self.prepare_prompt(session, moss, prompt)
                actions = self.get_actions(session)
                for action in actions:
                    if isinstance(action, PromptPipe):
                        prompt = action.update_prompt(prompt)

                # call llm
                llm = self.get_llmapi(session)
                messenger = session.messenger()
                llm.deliver_chat_completion(prompt, messenger)

                # handle actions
                messages, callers = messenger.flush()
                for caller in callers:
                    if caller.name in actions:
                        action = actions[caller.name]
                        op = action.run(session, caller)
                        if op is not None:
                            return op
                return session.self_wait()

    def filter_event(self, session: Session, event: Event) -> Union[Event, None]:
        return event

    def get_instructions(self, session: Session, moss: object) -> List[Message]:
        # instruction of moss agent is composed by:
        # 1. meta prompt.
        # 2. persona.
        # 3. instruction.
        # 4. props
        # 5. injections.
        # 6. contextual prompt.
        pass

    def prepare_prompt(self, session: Session, moss: object, prompt: Prompt) -> Prompt:
        pass

    def get_actions(self, session: Session) -> Dict[str, Action]:
        pass

    def get_llmapi(self, session: Session) -> LLMApi:
        llms = session.container.force_fetch(LLMs)
        llmapi_name = self.ghost.llmapi_name
        return llms.get_api(llmapi_name)

    def update_with_event(self, session: Session, event: Event) -> GoThreadInfo:
        session.thread.new_turn(event)
        return session.thread

    def get_compiler(self, session: Session) -> MossCompiler:
        pycontext = self.get_pycontext(session)

        compiler = session.container.force_fetch(MossCompiler)
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
        if injections:
            compiler = compiler.injects(**injections)
        return compiler

    def get_pycontext(self, session: Session) -> PyContext:
        pycontext_key = generate_import_path(PyContext)
        data = session.state.get(pycontext_key, None)
        if data is not None:
            pycontext = PyContext(**data)
        else:
            pycontext = PyContext(
                module=self.ghost.moss_module,
            )
        return pycontext


META_PROMPT = """
"""


class MossAction(Action, PromptPipe):

    def name(self) -> str:
        return "moss"

    def update_prompt(self, prompt: Prompt) -> Prompt:
        pass

    def run(self, session: Session, caller: Caller) -> Union[Operator, None]:
        pass
# </moss-hide>
