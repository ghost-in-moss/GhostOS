from typing import Union, Optional, Dict, Any, TypeVar, List, Self, Iterable
from types import ModuleType

from ghostos.identifier import Identifier
from pydantic import BaseModel, Field

from ghostos.helpers import import_from_path
from ghostos.prompter import TextPrmt, Prompter
from ghostos.abcd import GhostDriver, Operator, Agent, Session, StateValue, Action
from ghostos.core.runtime import Event, GoThreadInfo
from ghostos.core.moss import MossCompiler, PyContext, Moss, MossRuntime
from ghostos.core.messages import Message, Caller, Role
from ghostos.core.llms import (
    LLMs, LLMApi,
    Prompt, PromptPipe, AssistantNamePipe, run_prompt_pipeline,
    LLMFunc,
)
from .instructions import (
    GHOSTOS_INTRODUCTION, MOSS_INTRODUCTION, AGENT_INTRODUCTION, MOSS_FUNCTION_DESC,
    get_moss_context_prompter, get_agent_identity,
)
import json


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

    def get_artifact(self, session: Session) -> Optional[MossAgent.GoalType]:
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

        thread = self.update_with_event(session, event)

        compiler = self.get_compiler(session)
        with compiler:
            rtm = compiler.compile(self.ghost.compile_module)
            with rtm:
                # prepare instructions.
                instructions = self.get_instructions(session, rtm)
                # prepare prompt
                prompt = thread.to_prompt(instructions)
                pipes = self.get_prompt_pipes(session, rtm)
                prompt = run_prompt_pipeline(prompt, pipes)

                # prepare actions
                actions = self.get_actions(session, rtm)
                for action in actions:
                    # update prompt with action
                    if isinstance(action, PromptPipe):
                        prompt = action.update_prompt(prompt)

                # call llm
                llm = self.get_llmapi(session)
                messages = llm.deliver_chat_completion(prompt, not session.stream.completes_only())
                messages, callers = session.respond(messages, remember=True)

                # handle actions
                for caller in callers:
                    if caller.name in actions:
                        action = actions[caller.name]
                        op = action.run(session, caller)
                        if op is not None:
                            return op
                return session.flow().wait()

    def get_instructions(self, session: Session, moss_rtm: MossRuntime) -> List[Message]:
        """
        generate moss agent's instruction
        :param session:
        :param moss_rtm:
        :return:
        """
        prompter = self.get_instruction_prompter(session, moss_rtm)
        instruction = prompter.get_prompt(session.container, depth=0)
        return [Role.SYSTEM.new(content=instruction)]

    def get_instruction_prompter(self, session: Session, runtime: MossRuntime) -> Prompter:
        prompter = MossAgentPrompter.new(
            self.ghost,
            runtime,
        )
        return prompter

    def get_actions(self, session: Session, runtime: MossRuntime) -> Dict[str, Action]:
        """
        get moss agent's actions. default is moss action.
        """
        moss_action = MossAction(runtime)
        return {moss_action.name(): moss_action}

    def get_prompt_pipes(self, session: Session, runtime: MossRuntime) -> Iterable[PromptPipe]:
        yield AssistantNamePipe(self.ghost.name)

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
        # if magic function __agent_moss_injections__ exists, use it to get some instance level injections to moss.
        if __agent_moss_injections__.__name__ in module.__dict__:
            injection_fn = getattr(module, __agent_moss_injections__.__name__)
        injections = injection_fn(self.ghost, session)
        if injections:
            compiler = compiler.injects(**injections)
        return compiler

    def get_pycontext(self, session: Session) -> PyContext:
        """
        get moss pycontext. moss pycontext is bind to session.state as default.
        :param session:
        :return:
        """
        pycontext = SessionPyContext(
            module=self.ghost.moss_module,
        )
        return pycontext.get_or_bind(session)


class MossAgentPrompter(TextPrmt):

    @classmethod
    def new(cls, agent: MossAgent, runtime: MossRuntime) -> Self:
        children = [
            # system meta prompt
            TextPrmt(title="Meta Instruction", content=AGENT_INTRODUCTION).with_children(
                TextPrmt(title="GhostOS", content=GHOSTOS_INTRODUCTION),
                TextPrmt(title="MOSS", content=MOSS_INTRODUCTION),
                # code context
                get_moss_context_prompter("Code Context", runtime),
            ),
            # agent prompt
            TextPrmt(
                title="Agent Info",
                content="The Agent info about who you are and what you are doing: ",
            ).with_children(
                get_agent_identity("Identity", agent.__identifier__()),
                TextPrmt(title="Persona", content=agent.persona),
                TextPrmt(title="Instructions", content=agent.instruction),
            ),
        ]
        return cls().with_children(*children)


class SessionPyContext(PyContext, StateValue):

    def get(self, session: Session) -> Optional[Self]:
        data = session.state.get(SessionPyContext.__name__, None)
        if data is not None:
            if isinstance(data, Dict):
                return SessionPyContext(**data)
            elif isinstance(data, SessionPyContext):
                return data
        return None

    def bind(self, session: Session) -> None:
        session.state[SessionPyContext.__name__] = self


class MossAction(Action, PromptPipe):
    class Argument(BaseModel):
        code: str = Field(
            description="generated moss code",
        )

    def __init__(self, runtime: MossRuntime):
        self.runtime: MossRuntime = runtime

    def name(self) -> str:
        return "moss"

    def update_prompt(self, prompt: Prompt) -> Prompt:
        parameters = self.Argument.model_json_schema()
        llm_func = LLMFunc(
            name=self.name(),
            description=MOSS_FUNCTION_DESC,
            parameters=parameters,
        )
        prompt.functions.append(llm_func)
        return prompt

    def run(self, session: Session, caller: Caller) -> Union[Operator, None]:
        # prepare arguments.
        arguments = caller.arguments
        data = json.loads(arguments)
        args = self.Argument(**data)
        code = args.code.strip()

        # if code is not exists, inform the llm
        if not code:
            return self.fire_error(session, caller, "the moss code is empty")

        error = self.runtime.lint_exec_code(code)
        if error:
            return self.fire_error(session, caller, f"the moss code has syntax errors:\n{error}")

        moss = self.runtime.moss()
        try:
            result = self.runtime.execute(target="main", args=[moss])
            op = result.returns
            if op is not None and not isinstance(op, Operator):
                return self.fire_error(session, caller, "result of moss code is not None or Operator")
            pycontext = result.pycontext
            # rebind pycontext to bind session
            pycontext = SessionPyContext(**pycontext.model_dump(exclude_defaults=True))
            pycontext.bind(session)

            # handle std output
            std_output = result.std_output
            if std_output:
                output = f"Moss output:\n{std_output}"
                message = caller.new_output(output)
                if op is None:
                    # if std output is not empty, and op is none, observe the output as default.
                    return session.taskflow().think(message)
                else:
                    session.respond([message], remember=True)
            return op

        except Exception as e:
            return self.fire_error(session, caller, f"error executing moss code: {e}")

    @staticmethod
    def fire_error(session: Session, caller: Caller, error: str) -> Operator:
        message = caller.new_output(error)
        return session.taskflow().error(message)
