from typing import Optional, TypeVar, Dict, Any, Iterable
from .agent import MossAgent
from ghostos.core.moss import MossRuntime
from ghostos.abcd.concepts import Session, Operator
from ghostos.core.runtime import GoThreadInfo, Event
from ghostos.container import Provider

A = TypeVar("A")


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


def __moss_agent_creating__(agent: A, session: Session) -> None:
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
    from ghostos.abcd.thoughts import SummaryThought
    from ghostos.core.llms import Prompt

    thread = session.thread
    turns = thread.get_history_turns(True)
    # do the truncate
    if len(turns) > agent.truncate_at_turns:
        # the history turns to remove
        truncated = agent.truncate_at_turns - agent.truncate_to_turns
        if truncated <= 0:
            return thread
        turns = turns[:truncated]
        # last turn of the truncated turns
        if len(turns) < 1:
            return thread
        target = turns[-1]
        messages = []
        for turn in turns:
            messages.extend(turn.messages(False))
        prompt = Prompt(history=messages)
        _, summary = SummaryThought(llm_api=agent.llm_api).think(session, prompt)
        if summary:
            target.summary = summary
    return session.thread


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

# </moss-hide>
