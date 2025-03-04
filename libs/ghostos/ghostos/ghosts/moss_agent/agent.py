from typing import Union, Optional, List, Iterable, Tuple, TYPE_CHECKING
from warnings import warn

from ghostos_common.identifier import Identifier
from pydantic import Field

from ghostos_common.helpers import import_from_path
from ghostos_common.prompter import TextPOM, PromptObjectModel
from ghostos.abcd import (
    GhostDriver, Operator, Agent, Session, Action, Thought, Ghost, SessionPyContext,
    MossAction, MOSS_INTRODUCTION, get_moss_context_pom,
)
from ghostos.core.runtime import Event, GoThreadInfo
from ghostos_moss import MossCompiler, MossRuntime
from ghostos_common.entity import ModelEntity
from ghostos.core.messages import Role
from ghostos.core.llms import (
    PromptPipe, AssistantNamePipe, run_prompt_pipeline,
)
from ghostos.ghosts.moss_agent.instructions import (
    GHOSTOS_INTRODUCTION, AGENT_META_INTRODUCTION,
    get_agent_identity,
)
import json
from ghostos_container import Provider

if TYPE_CHECKING:
    from ghostos.ghosts.moss_agent.for_developer import BaseMossAgentMethods

__all__ = ['MossAgent', 'MossAgentDriver']


class MossAgent(ModelEntity, Agent):
    """
    Basic Agent that turn a python module into a conversational agent.

    Deprecated, this one is too complex during development.
    Use MossGhost instead!
    """

    """ subclass of MossAgent could have a GoalType, default is None"""

    moss_module: str = Field(description="Moss module name for the agent")
    persona: str = Field(description="Persona for the agent, if not given, use global persona")
    instruction: str = Field(description="The instruction that the agent should follow")

    # optional configs
    name: str = Field(default="", description="name of the agent")
    description: str = Field(default="", description="description of the agent")
    code: Optional[str] = Field(default=None, description="code override the module")
    compile_module: Optional[str] = Field(None, description="Compile module name for the agent")
    llm_api: str = Field(default="", description="name of the llm api, if none, use default one")
    truncate_at_turns: int = Field(default=40, description="when history turns reach the point, truncate")
    truncate_to_turns: int = Field(default=20, description="when truncate the history, left turns")

    def __identifier__(self) -> Identifier:
        name = self.name if self.name else self.moss_module
        return Identifier(
            id=self.moss_module,
            name=name,
            description=self.description,
        )


class MossAgentDriver(GhostDriver[MossAgent]):
    __custom_methods: Optional["BaseMossAgentMethods"] = None

    def __init__(self, ghost: MossAgent):
        super().__init__(ghost)
        warn(
            "MossAgentDriver is deprecated, use ghostos.ghosts.MossGhost instead",
            DeprecationWarning,
        )

    def get_custom_agent_methods(self) -> "BaseMossAgentMethods":
        from ghostos.ghosts.moss_agent.for_developer import BaseMossAgentMethods
        if self.__custom_methods is None:
            m = import_from_path(self.ghost.moss_module)
            # user can custom moss agent methods, by define a `MossAgentMethods` class
            self.__custom_methods = BaseMossAgentMethods.from_module(m)
        return self.__custom_methods

    def providers(self) -> Iterable[Provider]:
        """
        ghost session level providers
        """
        return self.get_custom_agent_methods().providers(self.ghost)

    def parse_event(self, session: Session, event: Event) -> Union[Event, None]:
        """
        parse the event before handle it. if return None, the event is ignored.
        :param session:
        :param event:
        :return:
        """
        return self.get_custom_agent_methods().agent_parse_event(self.ghost, session, event)

    def truncate(self, session: Session) -> GoThreadInfo:
        return self.get_custom_agent_methods().truncate_thread(self.ghost, session)

    def get_artifact(self, session: Session) -> Optional[MossAgent.ArtifactType]:
        from .for_meta_ai import __moss_agent_artifact__
        m = self.get_custom_agent_methods().module
        if __moss_agent_artifact__.__name__ not in m.__dict__:
            return None
        fn = getattr(m, __moss_agent_artifact__.__name__)
        compiler = self._get_moss_compiler(session)
        with compiler:
            runtime = compiler.compile(self.ghost.moss_module)
            with runtime:
                moss = runtime.moss()
                return fn(self.ghost, moss)

    def get_system_instruction(self, session: Session) -> str:
        compiler = self._get_moss_compiler(session)
        with compiler:
            rtm = compiler.compile(self.ghost.compile_module)
            with rtm:
                return self._get_instructions(session, rtm)

    def actions(self, session: Session) -> List[Action]:
        compiler = self._get_moss_compiler(session)
        with compiler:
            runtime = compiler.compile(self.ghost.moss_module)
            actions = self.get_actions(session, runtime)
            return list(actions)

    def thought(self, session: Session, runtime: MossRuntime) -> Thought:
        from .for_meta_ai import __moss_agent_thought__ as fn
        compiled = runtime.module()
        if fn.__name__ in compiled.__dict__:
            fn = compiled.__dict__[fn.__name__]
        return fn(self.ghost, runtime.moss(), *self.get_actions(session, runtime))

    def get_actions(self, session: Session, runtime: MossRuntime) -> Iterable[Action]:
        """
        get moss agent's actions. default is moss action.
        """
        from .for_meta_ai import __moss_agent_actions__ as fn
        compiled = runtime.module()
        if fn.__name__ in compiled.__dict__:
            fn = compiled.__dict__[fn.__name__]
        yield from fn(self.ghost, runtime.moss())
        # moss action at last
        moss_action = MossAction(runtime)
        yield moss_action

    def on_creating(self, session: Session) -> None:
        self.get_custom_agent_methods().on_creating(self.ghost, session)

    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        compiler = self._get_moss_compiler(session)
        with compiler:
            rtm = compiler.compile(self.ghost.compile_module)
            with rtm:
                # prepare instructions.
                op, ok = self._on_custom_event_handler(session, rtm, event)
                if ok:
                    return op or session.mindflow().wait()

                # prepare thread
                thread = session.thread
                thread.new_turn(event)

                # prepare prompt
                instructions = self._get_instructions(session, rtm)
                prompt = thread.to_prompt([Role.SYSTEM.new(content=instructions)], truncate=True)
                pipes = self._get_prompt_pipes(session, rtm)
                prompt = run_prompt_pipeline(prompt, pipes)

                # prepare actions
                thought = self.thought(session, rtm)
                prompt, op = thought.think(session, prompt)
                if op is not None:
                    return op
                return session.mindflow().wait()

    def _on_custom_event_handler(
            self,
            session: Session,
            runtime: MossRuntime,
            event: Event,
    ) -> Tuple[Optional[Event], bool]:
        method_name = "__moss_agent_on_" + event.type + "__"
        compiled = runtime.module()
        if method_name in compiled.__dict__:
            fn = compiled.__dict__[method_name]
            return fn(self.ghost, session, runtime, event), True
        return None, False

    def _get_instructions(self, session: Session, runtime: MossRuntime) -> str:
        """
        generate moss agent's instruction
        :param session:
        :param runtime:
        :return:
        """
        prompter = self._get_instruction_pom(session, runtime)
        instruction = prompter.get_prompt(session.container, depth=0)
        return instruction

    def _get_instruction_pom(self, session: Session, runtime: MossRuntime) -> PromptObjectModel:
        agent = self.ghost
        return TextPOM().with_children(
            # system meta prompt
            TextPOM(
                title="Meta Instruction",
                content=AGENT_META_INTRODUCTION,
            ).with_children(
                # ghostos meta instruction.
                TextPOM(title="GhostOS", content=GHOSTOS_INTRODUCTION),
                # the information about moss
                TextPOM(title="MOSS", content=MOSS_INTRODUCTION),

                # the moss providing context prompter.
                get_moss_context_pom("Code Context", runtime),
            ),
            # agent prompt
            TextPOM(
                title="Agent Info",
                content="The Agent info about who you are and what you are doing: ",
            ).with_children(
                get_agent_identity("Identity", agent.__identifier__()),
                TextPOM(title="Persona", content=self._get_agent_persona(session, runtime)),
                TextPOM(title="Instruction", content=self._get_agent_instruction(session, runtime)),
            ),
            TextPOM(
                title="Context",
                content="",
            ).with_children(
                self._get_context_prompter(session),
            )
        )

    def _get_agent_persona(self, session: Session, runtime: MossRuntime) -> str:
        from .for_meta_ai import __moss_agent_persona__ as fn
        compiled = runtime.module()
        if fn.__name__ in compiled.__dict__:
            fn = compiled.__dict__[fn.__name__]
        return fn(self.ghost, runtime.moss())

    def _get_agent_instruction(self, session: Session, runtime: MossRuntime) -> str:
        from .for_meta_ai import __moss_agent_instruction__ as fn
        compiled = runtime.module()
        if fn.__name__ in compiled.__dict__:
            fn = compiled.__dict__[fn.__name__]
        return fn(self.ghost, runtime.moss())

    def _get_context_prompter(self, session: Session) -> Optional[PromptObjectModel]:
        ctx = session.get_context()
        if ctx is None:
            return None
        return ctx

    def _get_prompt_pipes(self, session: Session, runtime: MossRuntime) -> Iterable[PromptPipe]:
        yield AssistantNamePipe(self.ghost.name)

    def _get_moss_compiler(self, session: Session) -> MossCompiler:
        from ghostos.ghosts.moss_agent.for_developer import __moss_agent_injections__
        pycontext = self.get_pycontext(session)

        compiler = session.container.force_fetch(MossCompiler)
        container = compiler.container()

        compiler = compiler.join_context(pycontext)
        compiler = compiler.with_locals(Optional=Optional)

        # register self
        container.set(Ghost, self.ghost)

        # bind moss agent itself
        compiler.bind(type(self.ghost), self.ghost)

        # bind agent level injections.
        fn = __moss_agent_injections__
        module = self.get_custom_agent_methods().module
        # if magic function __agent_moss_injections__ exists, use it to get some instance level injections to moss.
        if __moss_agent_injections__.__name__ in module.__dict__:
            fn = module.__dict__[__moss_agent_injections__.__name__]
        injections = fn(self.ghost, session)
        if injections:
            compiler = compiler.injects(**injections)
        return compiler

    def get_pycontext(self, session: Session) -> SessionPyContext:
        """
        get moss pycontext. moss pycontext is bind to session.state as default.
        :param session:
        :return:
        """
        pycontext = SessionPyContext(
            module=self.ghost.moss_module,
            code=self.ghost.code,
        )
        return pycontext.get_or_bind(session)
