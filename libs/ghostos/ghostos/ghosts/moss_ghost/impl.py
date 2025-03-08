import inspect
from typing import Union, Optional, Dict, List, Iterable, Tuple, ClassVar, Type, Any
from typing_extensions import Self
from types import ModuleType

from ghostos.core.llms import Prompt
from ghostos.ghosts.moss_agent.for_developer import BaseMossAgentMethods
from ghostos_common.identifier import Identifier
from pydantic import Field

from ghostos_common.helpers import import_from_path
from ghostos_common.prompter import TextPOM, PromptObjectModel
from ghostos_common.entity import ModelEntity
from ghostos.abcd import (
    GhostDriver, Operator, Agent, Session, Action, Thought, Ghost, ActionThought, ChainOfThoughts,
    SessionPyContext, MOSS_INTRODUCTION, get_moss_context_pom, MossAction,
    OpThought,
)
from ghostos.core.runtime import Event, GoThreadInfo
from ghostos_moss import MossCompiler, PyContext, MossRuntime, PromptAbleClass
from ghostos.core.messages import Role
from ghostos.core.llms import (
    PromptPipe, AssistantNamePipe, run_prompt_pipeline, ModelConf,
)
from ghostos.core.model_funcs import TruncateThreadByLLM
from ghostos_container import Provider
from ghostos_common.helpers import md5, yaml_pretty_dump, parse_import_path_module_and_attr_name

__all__ = ['MossGhost', 'MossGhostDriver', 'BaseMossGhostMethods']


class MossGhost(ModelEntity, Agent):
    """
    Basic Agent that turn a python module into a conversational agent.
    """

    """ subclass of MossAgent could have a GoalType, default is None"""

    # optional configs
    name: str = Field(description="name of the agent", pattern=r"^[a-zA-Z0-9_-]+$")
    module: str = Field(description="Moss module name for the agent")
    default_moss_type: Optional[str] = Field(
        default=None,
        description="default moss type for the module if Moss class not defined",
    )
    description: str = Field(default="", description="description of the agent")

    persona: str = Field(default="", description="Persona for the agent, if not given, use global persona")
    instruction: str = Field(default="", description="The instruction from agent developer")
    llm_api: str = Field(default="", description="The llm api to use. if empty use ghostos default llm api")
    model: Optional[ModelConf] = Field(default=None, description="The model to use, instead of the llm_api")

    safe_mode: bool = Field(default=False, description="if safe mode, anything unsafe shall be approve first")
    id: Optional[str] = Field(default=None, description="the id of the agent")

    def __identifier__(self) -> Identifier:
        name = self.name if self.name else self.modul
        if self.id:
            _id = self.id
        else:
            _id = md5(f"name:{name}|module:{self.module}|persona:{self.persona}|instruction:{self.instruction}")
        return Identifier(
            id=_id,
            name=name,
            description=self.description,
        )


class ContextPromptPipe(PromptPipe):
    def __init__(self, prompt_context: str):
        self.context = prompt_context

    def update_prompt(self, prompt: Prompt) -> Prompt:
        prompt.inputs.append(Role.new_system(
            content=self.context
        ))
        return prompt


class BaseMossGhostMethods(PromptAbleClass):
    """
    the Moss Ghost use the class MossGhostMethods inside the `moss module` (MossGhost.module) to drive its behavior
    developers can override this class to implement their own methods.
    """

    EXPECT_CLASS_NAME: ClassVar[str] = "MossGhostMethods"

    agent_meta_introduction: ClassVar[str] = """
You are the mind of an AI Agent driven by `GhostOS` framework.
Here are some basic information you might expect:
"""

    ghostos_introduction: ClassVar[str] = """
`GhostOS` is an AI Agent framework written in Python, 
providing llm connections, body shell, tools, memory etc and specially the `MOSS` for you.
"""

    def __init__(self, agent: MossGhost, module: ModuleType):
        self.module = module
        self.agent = agent
        self.modulename = agent.module
        self._moss_runtime: Optional[MossRuntime] = None

    def thought(self, session: Session, runtime: MossRuntime, actions: List[Action]) -> Thought[Operator]:
        """
        rewrite this method to define special thought for this agent.
        thought is a reusable unit for llm chain of thought.
        :param session:
        :param runtime:
        :param actions:
        :return:
        """
        return ChainOfThoughts(
            final=ActionThought(
                llm_api=self.agent.llm_api,
                actions=actions,
                model=self.agent.model,
                message_stage="",
            ),
            chain=self.get_thought_chain(session, runtime),
        )

    def get_thought_chain(self, session: Session, runtime: MossRuntime) -> List[OpThought]:
        return []

    def get_moss_providers(self) -> List[Provider]:
        return []

    def make_instruction_pom(self, session: Session, runtime: MossRuntime) -> PromptObjectModel:
        """
        rewrite this method to build the agent special runtime Prompt ObjectModel.
        :param session: the session
        :param runtime: moss runtime.
        :return: Prompt Object Model
        """
        agent = self.agent

        return TextPOM().with_children(
            # system meta prompt
            TextPOM(
                title="Meta Instruction",
                content=self.agent_meta_introduction,

            ).with_children(
                # ghostos meta instruction.
                TextPOM(title="GhostOS", content=self.ghostos_introduction),
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

                # the identity of the agent
                self.get_agent_identity("Identity", agent.__identifier__()),

                # the persona of the agent.
                TextPOM(title="Persona", content=self.get_persona(session, runtime)),

                # the instruction of the agent.
                TextPOM(title="Instruction", content=self.get_developer_instruction(session, runtime)),
            ),

        )

    def get_prompt_pipes(self, session: Session, runtime: MossRuntime) -> Iterable[PromptPipe]:
        """
        rewrite this method to define prompt pipes, before prompt send to thought.
        :param session:
        :param runtime:
        :return:
        """
        # clear agent self name from messages.
        context = session.get_context()
        if context is not None:
            prompt = context.get_prompt(session.container)
            yield ContextPromptPipe(prompt_context=prompt)

        yield AssistantNamePipe(self.agent.name)

    def providers(self) -> Iterable[Provider]:
        """
        define the session level providers.
        will bind to the session.container.
        """
        return []

    def parse_event(self, session: Session, event: Event) -> Union[Event, None]:
        """
        define custom logic to intercept an event
        :param session:
        :param event:
        """
        return event

    def moss_injections(self, session: Session) -> Dict[str, Any]:
        """
        define the injections needed for the Moss of this module.
        """
        return {}

    def get_artifact(self, session: Session) -> Optional[MossGhost.ArtifactType]:
        """
        :return: the artifact that this agent produced.
        """
        return None

    def truncate(self, session: Session) -> GoThreadInfo:
        """
        rewrite this method to define agent's own truncate thread logic.
        """
        thread = TruncateThreadByLLM(
            thread=session.thread,
            llm_api=self.agent.llm_api,
            truncate_at_turns=40,
            reduce_to_turns=20,
        ).run()
        return thread

    def get_actions(self, session: Session) -> List[Action]:
        """
        rewrite this method to define agent's actions.
        :param session:
        :return: the agent actions.
        """
        runtime = self.get_moss_runtime(session)
        yield MossAction(runtime)

    def on_custom_event_handler(
            self,
            session: Session,
            runtime: MossRuntime,
            event: Event,
    ) -> Tuple[Optional[Operator], bool]:
        """
        rewrite this method to define custom event handler.
        :param session:
        :param runtime:
        :param event:
        :return:
        """
        return None, False

    def default_pycontext(self) -> SessionPyContext:
        """
        define the default pycontext of this Moss Module.
        """
        return SessionPyContext(
            module=self.agent.module,
        )

    def get_pycontext(self, session: Session) -> PyContext:
        """
        get moss pycontext. moss pycontext is bind to session.state as default.
        :param session:
        :return:
        """
        # default pycontext.
        pycontext = self.default_pycontext()
        # get the bound pycontext from the session.
        return pycontext.get_or_bind(session)

    def is_safe_mode(self) -> bool:
        """
        :return: if the ghost is safe mode.
        """
        return self.agent.safe_mode

    def get_persona(self, session: Session, runtime: MossRuntime) -> str:
        return self.agent.persona

    def get_developer_instruction(self, session: Session, runtime: MossRuntime) -> str:
        return self.agent.instruction

    def on_creating(self, session: Session) -> None:
        """
        rewrite this method to define logic when the agent is created yet.
        :param session:
        """
        return

    def get_agent_identity(self, title: str, id_: Identifier) -> PromptObjectModel:
        value = id_.model_dump(exclude_defaults=True, exclude={"id"})
        return TextPOM(
            title=title,
            content=f"""
```yaml
{yaml_pretty_dump(value)}
```
"""
        )

    def make_system_instruction(self, session: Session, runtime: MossRuntime) -> str:
        """
        make the runtime system instruction for the thought prompt,
        :param session:
        :param runtime:
        :return:
        """
        prompter = self.make_instruction_pom(session, runtime)
        instruction = prompter.get_prompt(session.container, depth=0)
        return instruction

    def get_moss_compiler(self, session: Session) -> MossCompiler:
        pycontext = self.get_pycontext(session)
        compiler = session.container.force_fetch(MossCompiler)
        container = compiler.container()

        compiler = compiler.join_context(pycontext)
        compiler = compiler.with_locals(Optional=Optional, Operator=Operator)
        if self.agent.default_moss_type is not None:
            compiler = compiler.with_default_moss_type(self.agent.default_moss_type)

        # register moss level providers.
        for provider in self.get_moss_providers():
            compiler.register(provider)

        # register self
        container.set(Ghost, self.agent)
        compiler.bind(type(self.agent), self.agent)

        injections = self.moss_injections(session)
        if injections:
            compiler = compiler.injects(**injections)
        return compiler

    def get_system_instruction(self, session: Session) -> str:
        compiler = self.get_moss_compiler(session)
        with compiler:
            rtm = compiler.compile(self.agent.module)
            with rtm:
                return self.make_system_instruction(session, rtm)

    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        rtm = self.get_moss_runtime(session)
        with rtm:
            # prepare instructions.
            op, ok = self.on_custom_event_handler(session, rtm, event)
            if ok:
                return op or session.mindflow().wait()

            # prepare thread
            thread = session.thread
            thread.new_turn(event)

            # prepare prompt
            instruction = self.make_system_instruction(session, rtm)
            prompt = thread.to_prompt([
                Role.SYSTEM.new(content=instruction)],
                truncate=True,
            )
            pipes = self.get_prompt_pipes(session, rtm)
            prompt = run_prompt_pipeline(prompt, pipes)

            # prepare actions
            actions = self.get_actions(session)
            thought = self.thought(session, rtm, actions=actions)
            prompt, op = thought.think(session, prompt)
            if op is not None:
                return op

            # wait for response as default.
            return session.mindflow().wait()

    @classmethod
    def __class_prompt__(cls) -> str:
        """
        all the subclass of BaseMossAgentMethods is invisible to MossPrompter
        """
        return ""

    def get_moss_runtime(self, session: Session) -> MossRuntime:
        if self._moss_runtime is None:
            compiler = self.get_moss_compiler(session)
            with compiler:
                self._moss_runtime = compiler.compile(self.agent.module)
        return self._moss_runtime

    @classmethod
    def find_moss_ghost_methods(cls, module: ModuleType) -> Optional[Type[Self]]:
        wrapper = None
        if cls.EXPECT_CLASS_NAME in module.__dict__:
            wrapper = module.__dict__[cls.EXPECT_CLASS_NAME]
        else:
            for name, value in module.__dict__.items():
                if not inspect.isclass(value):
                    continue
                if value.__module__ != module.__name__:
                    continue
                if issubclass(value, BaseMossAgentMethods):
                    wrapper = value

        return wrapper

    @classmethod
    def new_from_module(cls, agent: MossGhost, module: ModuleType) -> Self:
        # 如果当前 module 存在 methods 定义, 用当前的.
        wrapper = cls.find_moss_ghost_methods(module)
        if wrapper is None:
            if agent.default_moss_type is not None:
                # 如果定义了 default moss type, 去目标目录找.
                default_moss_type_module_name, attr_name = parse_import_path_module_and_attr_name(
                    agent.default_moss_type,
                )
                default_moss_type_module = import_from_path(default_moss_type_module_name)
                wrapper = cls.find_moss_ghost_methods(default_moss_type_module)
        # 彻底找不到的话, 用默认的.
        if wrapper is None:
            wrapper = cls

        return wrapper(agent, module)

    def __del__(self):
        if self._moss_runtime is not None:
            self._moss_runtime.close()


class MossGhostDriver(GhostDriver[MossGhost], PromptAbleClass):
    """
    the moss ghost use the class exists in the `moss module`
    so this driver is just a proxy to MossGhostMethods
    """
    _methods: Optional[BaseMossGhostMethods] = None

    def get_methods(self) -> BaseMossGhostMethods:
        if self._methods is None:
            moss_module = import_from_path(self.ghost.module)
            self._methods = BaseMossGhostMethods.new_from_module(self.ghost, moss_module)
        return self._methods

    def get_artifact(self, session: Session) -> Optional[MossGhost.ArtifactType]:
        return self.get_methods().get_artifact(session)

    def get_system_instruction(self, session: Session) -> str:
        return self.get_methods().get_system_instruction(session)

    def actions(self, session: Session) -> List[Action]:
        return self.get_methods().get_actions(session)

    def providers(self) -> Iterable[Provider]:
        return self.get_methods().providers()

    def parse_event(self, session: Session, event: Event) -> Union[Event, None]:
        return self.get_methods().parse_event(session, event)

    def on_creating(self, session: Session) -> None:
        return self.get_methods().on_creating(session)

    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        return self.get_methods().on_event(session, event)

    def truncate(self, session: Session) -> GoThreadInfo:
        return self.get_methods().truncate(session)

    def is_safe_mode(self) -> bool:
        return self.get_methods().is_safe_mode()

    @classmethod
    def __class_prompt__(cls) -> str:
        """
        all the subclass of this driver is invisible to MossPrompter
        """
        return ""
