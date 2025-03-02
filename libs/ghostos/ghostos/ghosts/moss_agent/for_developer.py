from typing import Optional, TypeVar, Dict, Any, Iterable, Generic
from types import ModuleType
from ghostos.ghosts.moss_agent.agent import MossAgent
from ghostos_moss import MossRuntime
from ghostos.abcd.concepts import Session, Operator
from ghostos.core.runtime import GoThreadInfo, Event
from ghostos_container import Provider

A = TypeVar("A", bound=MossAgent)
F = TypeVar("F")


# <moss-hide>
# lifecycle methods for developer.
# agent need not know details about these methods, but also ok.
# hide these methods because too much ghostos designing patterns are needed.

def __moss_agent_providers__(agent: A) -> Iterable[Provider]:
    """
    return conversation level providers that specially required by the Agent.
    the conversation container will automatically register the providers and run them.

    :param agent: the moss agent instance.
    :return: providers that register to the session container.
    """
    return []


def __shell_providers__() -> Iterable[Provider]:
    """
    return shell level providers that specially required by the Agent.
    if the shell is running by `ghostos web` or `ghostos console`,
    the script will detect the __shell_providers__ attribute and register them into shell level container.

    You can consider the Shell is the body of an agent.
    So shell level providers usually register the body parts singletons, bootstrap them and register shutdown functions.
    """
    return []


def __moss_agent_on_creating__(agent: A, session: Session) -> None:
    """
    once a moss agent is creating,
    this function will be called.
    you can do something here to initialize Thread, Pycontext or Other things.
    """
    pass


def __moss_agent_truncate__(agent: MossAgent, session: Session) -> GoThreadInfo:
    """
    default history messages truncate logic of the agent
    :param agent:
    :param session:
    :return:
    """
    from ghostos.core.model_funcs import TruncateThreadByLLM

    thread = TruncateThreadByLLM(
        thread=session.thread,
        llm_api=agent.llm_api,
        truncate_at_turns=agent.truncate_at_turns,
        reduce_to_turns=agent.truncate_to_turns,
    ).run()
    return thread


def __moss_agent_parse_event__(agent: MossAgent, session: Session, event: Event) -> Optional[Event]:
    """
    when moss agent receive an event, will check it first before handle it.
    for example, if the user input is way too big, agent can ignore or reject the event here.
    :return: if None, the event will be ignored.
    """
    return event


def __moss_agent_injections__(agent: A, session: Session[A]) -> Dict[str, Any]:
    """
    manually define some of the injections to the Moss Class.
    if a property of Moss is not injected here, the session container will inject it by typehint.
    """
    return {
    }


def __moss_agent_on_event_type__(
        agent: MossAgent,
        session: Session[A],
        runtime: MossRuntime,
        event: Event,
) -> Optional[Operator]:
    """
    define customized event handler for each event type.
    the method name is the pattern `__moss_agent_on_[event_type]__`
    you may create any event type handler, instead of default logic in MossAgentDriver.
    """
    pass


class BaseMossAgentMethods(Generic[A]):
    """
    new way to define custom methods for Moss Agents.
    the magic methods are troublesome to copy,

    so developer can define a Subclass of MossAgentMethods at the target module,
    and rewrite the method do customized things.
    """
    MOSS_AGENT_METHODS_NAME = "MossAgentMethods"

    attr_prompts: Dict[str, str]

    @classmethod
    def from_module(cls, module: ModuleType) -> "BaseMossAgentMethods":
        name = cls.MOSS_AGENT_METHODS_NAME
        if name in module.__dict__:
            wrapper = module.__dict__[name]
        else:
            wrapper = cls
        return wrapper(module)

    def __init__(self, module: Optional[ModuleType] = None):
        self.module = module
        self.attr_prompts = {}

    def _get_module_func(self, expect: F, name: str = "") -> F:
        if self.module is None:
            return expect
        if not name:
            name = expect.__name__
        if name in self.module.__dict__:
            return self.module.__dict__[name]
        return expect

    def providers(self, agent: A) -> Iterable[Provider]:
        fn = self._get_module_func(__moss_agent_providers__)
        yield from fn(agent)

    def shell_providers(self) -> Iterable[Provider]:
        fn = self._get_module_func(__shell_providers__)
        yield from fn()

    def on_creating(self, agent: A, session: Session) -> None:
        fn = self._get_module_func(__moss_agent_on_creating__)
        return fn(agent, session)

    def truncate_thread(self, agent: MossAgent, session: Session) -> GoThreadInfo:
        fn = self._get_module_func(__moss_agent_truncate__)
        return fn(agent, session)

    def agent_parse_event(self, agent: MossAgent, session: Session, event: Event) -> Optional[Event]:
        fn = self._get_module_func(__moss_agent_parse_event__)
        return fn(agent, session, event)

    def agent_injections(self, agent: A, session: Session[A]) -> Dict[str, Any]:
        fn = self._get_module_func(__moss_agent_injections__)
        return fn(agent, session)

    def agent_on_event(
            self,
            agent: MossAgent,
            session: Session[A],
            runtime: MossRuntime,
            event: Event,
    ) -> Optional[Operator]:
        event_type = event.type
        fn_name = f"__moss_agent_on_{event_type}__"
        fn = self._get_module_func(__moss_agent_on_event_type__, fn_name)
        return fn(agent, session, runtime, event)

    def __prompt__(self) -> str:
        return ""

# </moss-hide>
