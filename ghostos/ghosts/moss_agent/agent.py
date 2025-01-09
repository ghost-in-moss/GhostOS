from typing import Union, Optional, Dict, List, Iterable, Tuple, ClassVar
from typing_extensions import Self
from types import ModuleType

from ghostos.identifier import Identifier
from pydantic import BaseModel, Field

from ghostos.helpers import import_from_path
from ghostos.prompter import TextPrmt, Prompter
from ghostos.abcd import GhostDriver, Operator, Agent, Session, StateValue, Action, Thought, Ghost
from ghostos.core.runtime import Event, GoThreadInfo
from ghostos.core.moss import MossCompiler, PyContext, MossRuntime
from ghostos.entity import ModelEntity
from ghostos.core.messages import FunctionCaller, Role
from ghostos.core.llms import (
    Prompt, PromptPipe, AssistantNamePipe, run_prompt_pipeline,
    LLMFunc,
)
from .instructions import (
    GHOSTOS_INTRODUCTION, MOSS_INTRODUCTION, AGENT_META_INTRODUCTION, MOSS_FUNCTION_DESC,
    get_moss_context_prompter, get_agent_identity,
)
import json

from ghostos.container import Provider

__all__ = ['MossAgent', 'MossAgentDriver', 'MossAction']


class MossAgent(ModelEntity, Agent):
    """
    Basic Agent that turn a python module into a conversational agent.
    """

    """ subclass of MossAgent could have a GoalType, default is None"""

    moss_module: str = Field(description="Moss module name for the agent")
    persona: str = Field(description="Persona for the agent, if not given, use global persona")
    instructions: str = Field(description="The instruction that the agent should follow")

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

    def get_module(self) -> ModuleType:
        m = import_from_path(self.ghost.moss_module)
        return m

    def providers(self) -> Iterable[Provider]:
        """
        ghost session level providers
        """
        from ghostos.ghosts.moss_agent.for_developer import __moss_agent_providers__
        m = self.get_module()
        fn = __moss_agent_providers__
        if __moss_agent_providers__.__name__ in m.__dict__:
            fn = m.__dict__[__moss_agent_providers__.__name__]
        return fn(self.ghost)

    def parse_event(self, session: Session, event: Event) -> Union[Event, None]:
        """
        parse the event before handle it. if return None, the event is ignored.
        :param session:
        :param event:
        :return:
        """
        from ghostos.ghosts.moss_agent.for_developer import __moss_agent_parse_event__
        fn = __moss_agent_parse_event__
        if __moss_agent_parse_event__.__name__ in event.__dict__:
            fn = event.__dict__[__moss_agent_parse_event__.__name__]
        return fn(self.ghost, session, event)

    def truncate(self, session: Session) -> GoThreadInfo:
        from ghostos.ghosts.moss_agent.for_developer import __moss_agent_truncate__
        fn = __moss_agent_truncate__
        if __moss_agent_truncate__.__name__ in session.__dict__:
            fn = session.__dict__[__moss_agent_truncate__.__name__]
        return fn(self.ghost, session)

    def get_artifact(self, session: Session) -> Optional[MossAgent.ArtifactType]:
        from .for_meta_ai import __moss_agent_artifact__
        m = self.get_module()
        if __moss_agent_artifact__.__name__ not in m.__dict__:
            return None
        fn = getattr(m, __moss_agent_artifact__.__name__)
        compiler = self._get_moss_compiler(session)
        with compiler:
            runtime = compiler.compile(self.ghost.moss_module)
            with runtime:
                moss = runtime.moss()
                return fn(self.ghost, moss)

    def get_instructions(self, session: Session) -> str:
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
        from ghostos.ghosts.moss_agent.for_developer import __moss_agent_creating__ as fn
        m = self.get_module()
        if fn.__name__ in m.__dict__:
            fn = m.__dict__[fn.__name__]
        fn(self.ghost, session)
        return

    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        compiler = self._get_moss_compiler(session)
        with compiler:
            rtm = compiler.compile(self.ghost.compile_module)
            with rtm:
                # prepare instructions.
                op, ok = self._on_custom_event_handler(session, rtm, event)
                if ok:
                    return op or session.taskflow().wait()

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
                return session.taskflow().wait()

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
        prompter = self._get_instruction_prompter(session, runtime)
        instruction = prompter.get_prompt(session.container, depth=0)
        return instruction

    def _get_instruction_prompter(self, session: Session, runtime: MossRuntime) -> Prompter:
        agent = self.ghost
        return TextPrmt().with_children(
            # system meta prompt
            TextPrmt(
                title="Meta Instruction",
                content=AGENT_META_INTRODUCTION,
            ).with_children(
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
                TextPrmt(title="Persona", content=self._get_agent_persona(session, runtime)),
                TextPrmt(title="Instruction", content=self._get_agent_instruction(session, runtime)),
            ),
            TextPrmt(
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

    def _get_context_prompter(self, session: Session) -> Optional[Prompter]:
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
        module = self.get_module()
        # if magic function __agent_moss_injections__ exists, use it to get some instance level injections to moss.
        if __moss_agent_injections__.__name__ in module.__dict__:
            fn = module.__dict__[__moss_agent_injections__.__name__]
        injections = fn(self.ghost, session)
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
            code=self.ghost.code,
        )
        return pycontext.get_or_bind(session)


class SessionPyContext(PyContext, StateValue):
    """
    bind pycontext to session.state
    """

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
    DEFAULT_NAME: ClassVar[str] = "moss"

    class Argument(BaseModel):
        code: str = Field(description="the python code you want to execute. never quote them with ```")

    def __init__(self, runtime: MossRuntime, name: str = DEFAULT_NAME):
        self.runtime: MossRuntime = runtime
        self._name = name

    def name(self) -> str:
        return self._name

    def as_function(self) -> Optional[LLMFunc]:
        parameters = self.Argument.model_json_schema()
        llm_func = LLMFunc(
            name=self.name(),
            description=MOSS_FUNCTION_DESC,
            parameters=parameters,
        )
        return llm_func

    def update_prompt(self, prompt: Prompt) -> Prompt:
        llm_func = self.as_function()
        if llm_func is not None:
            prompt.functions.append(llm_func)
        return prompt

    @classmethod
    def unmarshal_arguments(cls, arguments: str) -> str:
        try:
            if arguments.startswith("{"):
                if not arguments.endswith("}"):
                    arguments += "}"
                data = json.loads(arguments)
                args = cls.Argument(**data)
            else:
                args = cls.Argument(code=arguments)
        except Exception:
            args = cls.Argument(code=arguments)
        code = args.code.strip()
        if code.startswith("```python"):
            code.lstrip("```python")
        if code.startswith("```"):
            code.lstrip("```")
        if code.endswith("```"):
            code.rstrip("```")
        return code.strip()

    def run(self, session: Session, caller: FunctionCaller) -> Union[Operator, None]:
        session.logger.debug("MossAction receive caller: %s", caller)
        # prepare arguments.
        arguments = caller.arguments
        code = self.unmarshal_arguments(arguments)
        if code.startswith("{") and code.endswith("}"):
            # unmarshal again.
            code = self.unmarshal_arguments(code)

        # if code is not exists, inform the llm
        if not code:
            return self.fire_error(session, caller, "the moss code is empty")
        session.logger.debug("moss action code: %s", code)

        error = self.runtime.lint_exec_code(code)
        if error:
            return self.fire_error(session, caller, f"the moss code has syntax errors:\n{error}")

        moss = self.runtime.moss()
        try:
            result = self.runtime.execute(target="run", code=code, args=[moss])
            op = result.returns
            if op is not None and not isinstance(op, Operator):
                return self.fire_error(session, caller, "result of moss code is not None or Operator")
            pycontext = result.pycontext
            # rebind pycontext to bind session
            pycontext = SessionPyContext(**pycontext.model_dump(exclude_defaults=True))
            pycontext.bind(session)

            # handle std output
            std_output = result.std_output
            session.logger.debug("moss action std_output: %s", std_output)
            if std_output:
                output = f"Moss output:\n{std_output}"
                message = caller.new_output(output)
                session.respond([message])
                if op is None:
                    # if std output is not empty, and op is none, observe the output as default.
                    return session.taskflow().think()
            else:
                output = caller.new_output("executed")
                session.respond([output])
                return None

        except Exception as e:
            session.logger.exception(e)
            return self.fire_error(session, caller, f"error during executing moss code: {e}")

    @staticmethod
    def fire_error(session: Session, caller: FunctionCaller, error: str) -> Operator:
        message = caller.new_output(error)
        session.respond([message])
        return session.taskflow().error()
